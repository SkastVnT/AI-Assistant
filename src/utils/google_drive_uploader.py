"""
Google Drive Uploader Utility
Handles uploading files and folders to Google Drive using OAuth 2.0
"""

import os
import pickle
from pathlib import Path
from typing import Optional, List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Scopes required for Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveUploader:
    """Handles file uploads to Google Drive"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize Google Drive uploader
        
        Args:
            credentials_path: Path to OAuth credentials JSON file
            token_path: Path to save/load token pickle file
        """
        self.project_root = Path(__file__).parent.parent.parent
        
        # Default paths
        if credentials_path is None:
            credentials_path = self.project_root / "config" / "google_oauth_credentials.json"
        if token_path is None:
            token_path = self.project_root / "config" / "token.pickle"
            
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.creds = None
        self.service = None
        
        # Authenticate on initialization
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        # Load token if exists
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at: {self.credentials_path}\n"
                        f"Please download from Google Cloud Console and place at config/google_oauth_credentials.json"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        # Build service
        self.service = build('drive', 'v3', credentials=self.creds)
        print(f"✅ Authenticated with Google Drive")
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name: Name of folder to create
            parent_folder_id: ID of parent folder (None for root)
            
        Returns:
            Folder ID
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name'
            ).execute()
            
            print(f"📁 Created folder: {folder.get('name')} (ID: {folder.get('id')})")
            return folder.get('id')
            
        except HttpError as error:
            print(f"❌ Error creating folder: {error}")
            raise
    
    def upload_file(
        self, 
        file_path: str, 
        folder_id: Optional[str] = None,
        file_name: Optional[str] = None
    ) -> Dict:
        """
        Upload a single file to Google Drive
        
        Args:
            file_path: Path to file to upload
            folder_id: ID of folder to upload to (None for root)
            file_name: Custom name for file (None to use original)
            
        Returns:
            File metadata dict with 'id', 'name', 'webViewLink'
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_metadata = {
                'name': file_name or file_path.name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_path)
            
            media = MediaFileUpload(
                str(file_path),
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, size'
            ).execute()
            
            size_mb = int(file.get('size', 0)) / (1024 * 1024)
            print(f"✅ Uploaded: {file.get('name')} ({size_mb:.2f} MB)")
            print(f"   Link: {file.get('webViewLink')}")
            
            return file
            
        except HttpError as error:
            print(f"❌ Error uploading {file_path.name}: {error}")
            raise
    
    def upload_folder(
        self, 
        folder_path: str, 
        parent_folder_id: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict:
        """
        Upload entire folder to Google Drive
        
        Args:
            folder_path: Path to folder to upload
            parent_folder_id: ID of parent folder in Drive
            exclude_patterns: List of patterns to exclude (e.g., ['*.pyc', '__pycache__'])
            
        Returns:
            Dict with folder_id and list of uploaded files
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '*.pyc', '*.log', 'venv*', '.git']
        
        # Create root folder in Drive
        folder_id = self.create_folder(folder_path.name, parent_folder_id)
        
        uploaded_files = []
        folder_cache = {}  # Cache để tránh tạo lại folder
        
        # Upload files
        for item in folder_path.rglob('*'):
            # Skip excluded patterns
            if any(item.match(pattern) for pattern in exclude_patterns):
                continue
            
            if item.is_file():
                try:
                    # Calculate relative path
                    rel_path = item.relative_to(folder_path)
                    
                    # Create parent folders if needed
                    current_folder_id = folder_id
                    if rel_path.parent != Path('.'):
                        # Use cache để tránh tạo duplicate folders
                        folder_key = str(rel_path.parent)
                        if folder_key not in folder_cache:
                            folder_cache[folder_key] = self._ensure_folder_path(
                                rel_path.parent, folder_id, folder_cache
                            )
                        current_folder_id = folder_cache[folder_key]
                    
                    # Upload file
                    file_info = self.upload_file(
                        str(item), 
                        current_folder_id
                    )
                    uploaded_files.append(file_info)
                    
                except Exception as e:
                    print(f"⚠️  Skipping {item.name}: {e}")
        
        return {
            'folder_id': folder_id,
            'folder_name': folder_path.name,
            'uploaded_files': uploaded_files,
            'total_files': len(uploaded_files)
        }
    
    def _ensure_folder_path(self, path: Path, parent_id: str, cache: Dict = None) -> str:
        """Recursively create folder path and return final folder ID"""
        if cache is None:
            cache = {}
            
        if path == Path('.'):
            return parent_id
        
        # Check cache first
        cache_key = str(path)
        if cache_key in cache:
            return cache[cache_key]
        
        # Create parent first
        if path.parent != Path('.'):
            parent_cache_key = str(path.parent)
            if parent_cache_key not in cache:
                cache[parent_cache_key] = self._ensure_folder_path(path.parent, parent_id, cache)
            parent_id = cache[parent_cache_key]
        
        # Create this folder
        folder_id = self.create_folder(path.name, parent_id)
        cache[cache_key] = folder_id
        return folder_id
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Determine MIME type from file extension"""
        extension = file_path.suffix.lower()
        
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.json': 'application/json',
            '.yaml': 'application/x-yaml',
            '.yml': 'application/x-yaml',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.csv': 'text/csv',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.sql': 'text/plain',
            '.db': 'application/x-sqlite3',
            '.zip': 'application/zip',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
        }
        
        return mime_types.get(extension, 'application/octet-stream')
    
    def list_files(self, folder_id: Optional[str] = None, max_results: int = 100) -> List[Dict]:
        """
        List files in a folder
        
        Args:
            folder_id: Folder ID to list (None for all files)
            max_results: Maximum number of results
            
        Returns:
            List of file metadata dicts
        """
        try:
            query = f"'{folder_id}' in parents" if folder_id else None
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, size, createdTime, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                print('📭 No files found.')
            else:
                print(f'📂 Found {len(files)} files:')
                for file in files:
                    size_mb = int(file.get('size', 0)) / (1024 * 1024) if file.get('size') else 0
                    print(f"   - {file['name']} ({size_mb:.2f} MB)")
            
            return files
            
        except HttpError as error:
            print(f"❌ Error listing files: {error}")
            raise


def quick_upload_docs(uploader: GoogleDriveUploader) -> Dict:
    """Quick function to upload docs folder"""
    project_root = Path(__file__).parent.parent.parent
    docs_path = project_root / "docs"
    
    return uploader.upload_folder(
        str(docs_path),
        exclude_patterns=['archives', '__pycache__', '*.pyc', '*.log']
    )


def quick_upload_scripts(uploader: GoogleDriveUploader) -> Dict:
    """Quick function to upload scripts folder"""
    project_root = Path(__file__).parent.parent.parent
    scripts_path = project_root / "scripts"
    
    return uploader.upload_folder(
        str(scripts_path),
        exclude_patterns=['__pycache__', '*.pyc', '*.log', 'venv*']
    )


def quick_upload_database(uploader: GoogleDriveUploader) -> Dict:
    """Quick function to upload database folder"""
    project_root = Path(__file__).parent.parent.parent
    database_path = project_root / "database"
    
    return uploader.upload_folder(
        str(database_path),
        exclude_patterns=['__pycache__', '*.pyc', '*.log']
    )


if __name__ == "__main__":
    # Example usage
    print("🚀 Google Drive Uploader Test")
    print("=" * 50)
    
    try:
        # Initialize uploader
        uploader = GoogleDriveUploader()
        
        # Example: Upload single file
        # uploader.upload_file("README.md")
        
        # Example: Create folder and upload file
        # folder_id = uploader.create_folder("AI-Assistant-Backup")
        # uploader.upload_file("README.md", folder_id)
        
        # Example: Upload entire folder
        # result = quick_upload_docs(uploader)
        # print(f"\n✅ Uploaded {result['total_files']} files")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
