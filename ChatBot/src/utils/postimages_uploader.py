"""
PostImages Free Image Hosting
No API key required!
URL: https://postimages.org/

Features:
- Free unlimited uploads
- No registration needed
- Permanent URLs (no expiration)
- Fast CDN delivery
"""

import requests
import logging
from pathlib import Path
from typing import Optional, Dict
import json

logger = logging.getLogger(__name__)


class PostImagesUploader:
    """Upload images to PostImages.org (free, no API key needed)"""
    
    UPLOAD_URL = "https://postimages.org/json/rr"
    
    @staticmethod
    def upload_image(image_path: str, title: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Upload image to PostImages
        
        Args:
            image_path: Path to image file
            title: Optional image title (not used by PostImages but kept for API compatibility)
            
        Returns:
            Dict with:
                - url: Direct image URL (e.g., https://i.postimg.cc/abc123/image.png)
                - delete_url: URL to delete the image
                - thumbnail_url: Thumbnail URL
                - page_url: PostImages page URL
                - filename: Original filename
                
        Example:
            >>> uploader = PostImagesUploader()
            >>> result = uploader.upload_image("test.png")
            >>> print(result['url'])
            https://i.postimg.cc/abc123/test.png
        """
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                logger.error(f"❌ Image not found: {image_path}")
                return None
            
            # Validate file is image
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            if image_path.suffix.lower() not in valid_extensions:
                logger.error(f"❌ Invalid image format: {image_path.suffix}")
                return None
            
            logger.info(f"📤 Uploading {image_path.name} to PostImages...")
            
            # Read image file
            with open(image_path, 'rb') as f:
                files = {
                    'file': (image_path.name, f, f'image/{image_path.suffix[1:]}')
                }
                
                data = {
                    'upload_session': '',
                    'numfiles': '1',
                    'gallery': '',
                    'ui': 'json'
                }
                
                response = requests.post(
                    PostImagesUploader.UPLOAD_URL,
                    files=files,
                    data=data,
                    timeout=120  # Increase timeout for large images (was 60)
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        
                        # Check if upload was successful
                        if result.get('status') == 'OK' or 'url' in result:
                            image_url = result.get('url')
                            
                            if not image_url:
                                logger.error(f"❌ No URL in response: {result}")
                                return None
                            
                            logger.info(f"✅ Upload successful!")
                            logger.info(f"🔗 URL: {image_url}")
                            
                            return {
                                'url': image_url,
                                'delete_url': result.get('delete', ''),
                                'thumbnail_url': result.get('thumb', ''),
                                'page_url': result.get('page', ''),
                                'filename': image_path.name,
                                'size': image_path.stat().st_size,
                                'service': 'postimages'
                            }
                        else:
                            error_msg = result.get('error', result.get('msg', 'Unknown error'))
                            logger.error(f"❌ Upload failed: {error_msg}")
                            return None
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON response: {response.text[:200]}")
                        logger.error(f"JSON decode error: {e}")
                        return None
                else:
                    logger.error(f"❌ HTTP {response.status_code}")
                    logger.error(f"Response: {response.text[:200]}")
                    return None
                    
        except requests.exceptions.Timeout:
            logger.error("❌ Upload timeout (>60s)")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def delete_image(delete_url: str) -> bool:
        """
        Delete uploaded image from PostImages
        
        Args:
            delete_url: Delete URL from upload response
            
        Returns:
            True if deleted successfully
            
        Example:
            >>> PostImagesUploader.delete_image("https://postimg.cc/delete/...")
            True
        """
        try:
            if not delete_url:
                logger.warning("No delete URL provided")
                return False
                
            logger.info(f"🗑️ Deleting image from PostImages...")
            
            response = requests.get(delete_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Image deleted successfully")
                return True
            else:
                logger.warning(f"⚠️ Delete failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Delete error: {e}")
            return False


# Quick helper function
def upload_to_postimages(image_path: str, title: Optional[str] = None) -> Optional[str]:
    """
    Quick upload to PostImages and return URL
    
    Args:
        image_path: Path to image file
        title: Optional title (not used but kept for API compatibility)
        
    Returns:
        Direct image URL or None if failed
        
    Example:
        >>> url = upload_to_postimages("generated.png")
        >>> print(url)
        https://i.postimg.cc/abc123/generated.png
    """
    result = PostImagesUploader.upload_image(image_path, title)
    return result['url'] if result else None


# Test script
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("PostImages Uploader - Test Script")
        print("="*60)
        print("\nUsage: python postimages_uploader.py <image_path>")
        print("Example: python postimages_uploader.py test.png\n")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("\n" + "="*60)
    print("🧪 TESTING POSTIMAGES UPLOAD")
    print("="*60)
    print(f"📁 File: {image_path}")
    
    if Path(image_path).exists():
        print(f"📦 Size: {Path(image_path).stat().st_size:,} bytes")
    
    print("="*60 + "\n")
    
    result = PostImagesUploader.upload_image(image_path)
    
    if result:
        print("\n" + "="*60)
        print("✅ UPLOAD SUCCESS!")
        print("="*60)
        print(f"🔗 Image URL:     {result['url']}")
        print(f"🌐 Page URL:      {result['page_url']}")
        print(f"🖼️  Thumbnail URL: {result['thumbnail_url']}")
        print(f"🗑️  Delete URL:    {result['delete_url']}")
        print(f"📦 Size:          {result['size']:,} bytes")
        print(f"📝 Service:       {result['service']}")
        print("="*60)
        print("\n💡 Copy URL above and paste into browser to view!\n")
    else:
        print("\n" + "="*60)
        print("❌ UPLOAD FAILED!")
        print("="*60)
        print("Check the error messages above for details.\n")
        sys.exit(1)
