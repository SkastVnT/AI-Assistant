"""
ImgBB image upload utility
"""
import requests
import base64
from pathlib import Path
import logging
import time

logger = logging.getLogger(__name__)


class ImgBBUploader:
    """Upload images to ImgBB and get shareable links"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.upload_url = "https://api.imgbb.com/1/upload"
    
    def upload_image(self, image_path, name=None, max_retries=3):
        """
        Upload image to ImgBB with retry logic
        
        Args:
            image_path: Path to image file (str, Path, or file-like object)
            name: Optional image name
            max_retries: Maximum number of retry attempts
            
        Returns:
            dict with 'url', 'delete_url', 'display_url' keys
        """
        # Handle different input types (str, Path, TemporaryFileWrapper, etc.)
        if hasattr(image_path, 'name'):
            # File-like object (e.g., TemporaryFileWrapper from Gradio)
            image_path = Path(image_path.name)
        else:
            image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Read and encode image
        with open(image_path, 'rb') as file:
            image_data = base64.b64encode(file.read()).decode('utf-8')
        
        # Prepare request
        payload = {
            'key': self.api_key,
            'image': image_data,
        }
        
        if name:
            payload['name'] = name
        
        # Try upload with retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Uploading {image_path.name} to ImgBB... (attempt {attempt + 1}/{max_retries})")
                
                # Increase timeout for large images
                response = requests.post(
                    self.upload_url, 
                    data=payload, 
                    timeout=(10, 60)  # (connect timeout, read timeout)
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('success'):
                    data = result['data']
                    logger.info(f"Upload successful: {data['url']}")
                    return {
                        'url': data['url'],  # Direct image URL
                        'display_url': data['url_viewer'],  # ImgBB page
                        'delete_url': data.get('delete_url'),
                        'size': data.get('size'),
                        'width': data.get('width'),
                        'height': data.get('height'),
                    }
                else:
                    raise Exception(f"Upload failed: {result.get('error', {}).get('message', 'Unknown error')}")
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} upload attempts failed")
                    raise
            except Exception as e:
                logger.error(f"ImgBB upload error: {e}")
                raise


def upload_to_imgbb(image_path, api_key, name=None):
    """
    Convenience function to upload image
    
    Returns:
        Direct image URL or None if failed
    """
    try:
        uploader = ImgBBUploader(api_key)
        result = uploader.upload_image(image_path, name)
        return result['url']
    except Exception as e:
        logger.error(f"Failed to upload to ImgBB: {e}")
        return None
