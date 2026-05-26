"""
Google Drive upload service using Service Account.
Direct upload without needing OAuth or webhook.
"""

import importlib
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Google Drive upload service using Service Account"""

    _instance = None
    _service = None
    _folder_id = None
    _media_upload_cls = None
    _quota_exceeded = False  # set after first storageQuotaExceeded — stops log spam

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._service is None:
            self._initialize()

    def _initialize(self):
        """Initialize Google Drive service with Service Account"""
        try:
            service_account = importlib.import_module("google.oauth2.service_account")
            discovery = importlib.import_module("googleapiclient.discovery")
            http_mod = importlib.import_module("googleapiclient.http")
        except ImportError:
            logger.warning("[GoogleDrive] google-auth library not available")
            return

        sa_path = os.getenv("GOOGLE_DRIVE_SA_JSON_PATH", "")
        chatbot_root = Path(__file__).resolve().parents[1]
        resolved = Path(sa_path)
        if not resolved.is_absolute():
            resolved = (chatbot_root / resolved).resolve()

        if not sa_path or not resolved.exists():
            logger.warning(
                f"[GoogleDrive] Service account JSON not found at {resolved}"
            )
            return

        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(resolved), scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            self._service = discovery.build("drive", "v3", credentials=credentials)
            self._media_upload_cls = http_mod.MediaIoBaseUpload
            logger.info("[GoogleDrive] Service initialized successfully")
        except Exception as e:
            logger.error(f"[GoogleDrive] Failed to initialize: {e}")
            self._service = None

    def set_folder_id(self, folder_id: str):
        """Set the target Drive folder ID"""
        self._folder_id = folder_id

    def upload_image(
        self, image_b64: str, filename: str = None, metadata: dict = None
    ) -> dict[str, Any]:
        """
        Upload base64 image to Google Drive.

        Args:
            image_b64: Base64 encoded image (can include data URL prefix)
            filename: Optional filename for the image
            metadata: Optional metadata dict

        Returns:
            {
                'success': bool,
                'file_id': str or None,
                'web_view_link': str or None,
                'error': str or None
            }
        """
        result = {
            "success": False,
            "file_id": None,
            "web_view_link": None,
            "error": None,
        }

        if self._service is None:
            result["error"] = "Google Drive service not initialized"
            return result

        if self._quota_exceeded:
            result["error"] = "Google Drive quota exceeded (disabled for this session)"
            return result

        try:
            # Clean base64 (remove data URL prefix if present)
            if "base64," in image_b64:
                image_b64 = image_b64.split("base64,")[1]

            # Decode base64 to bytes
            import base64

            image_bytes = base64.b64decode(image_b64)

            # Create file metadata
            file_metadata = {
                "name": filename
                or f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "mimeType": "image/png",
            }

            # Add to folder if specified
            if self._folder_id:
                file_metadata["parents"] = [self._folder_id]

            # Create media upload
            media_cls = self._media_upload_cls
            if media_cls is None:
                result["error"] = "Google Drive media uploader not initialized"
                return result

            media = media_cls(
                io.BytesIO(image_bytes), mimetype="image/png", resumable=True
            )

            # Upload file — supportsAllDrives enables Shared Drive uploads
            file = (
                self._service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink,parents",
                    supportsAllDrives=True,
                )
                .execute()
            )

            if file and file.get("id"):
                result["success"] = True
                result["file_id"] = file["id"]
                result["web_view_link"] = file.get("webViewLink", "")
                logger.info(f"[GoogleDrive] Image uploaded: {file['id']}")
            else:
                result["error"] = "Upload succeeded but no file ID returned"

        except Exception as e:
            err_str = str(e)
            result["error"] = err_str
            if "storageQuotaExceeded" in err_str or "quotaExceeded" in err_str:
                if not self._quota_exceeded:
                    self._quota_exceeded = True
                    logger.warning(
                        "[GoogleDrive] Service Account has no Drive quota. "
                        "Disabling Drive uploads for this session. "
                        "Set GOOGLE_DRIVE_ENABLED=false to silence this at startup."
                    )
            else:
                logger.error(f"[GoogleDrive] Upload failed: {e}")

        return result
