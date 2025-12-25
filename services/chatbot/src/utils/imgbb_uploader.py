"""
ImgBB Free Image Hosting
Free API: https://api.imgbb.com/
Easy to get API key (no credit card)
"""

import os
import requests
import base64
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ImgBBUploader:
    """Upload images to ImgBB (free, easy API key)"""
    
    API_URL = "https://api.imgbb.com/1/upload"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ImgBB uploader
        
        Args:
            api_key: ImgBB API key (from .env IMGBB_API_KEY)
        """
        self.api_key = api_key or os.getenv('IMGBB_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "ImgBB API key not found!\n"
                "Get one from: https://api.imgbb.com/\n"
                "Then add to .env: IMGBB_API_KEY=your_key_here"
            )
    
    def upload(self, image_data: str, title: Optional[str] = None, 
               expiration: int = 0) -> Optional[Dict[str, str]]:
        """
        Upload base64 image to ImgBB (for API use)
        
        Args:
            image_data: Base64 encoded image string
            title: Optional image title
            expiration: Auto-delete after seconds (0 = never, max 15552000 = 180 days)
            
        Returns:
            Dict with URLs or None if failed
        """
        try:
            logger.info(f"📤 Uploading base64 image to ImgBB...")
            
            # Prepare payload
            payload = {
                'key': self.api_key,
                'image': image_data,
                'name': title or 'AI_Generated',
            }
            
            if expiration > 0:
                payload['expiration'] = min(expiration, 15552000)
            
            response = requests.post(
                self.API_URL,
                data=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    data = result['data']
                    
                    logger.info(f"✅ Upload successful!")
                    logger.info(f"🔗 URL: {data['url']}")
                    
                    return {
                        'url': data['url'],
                        'display_url': data['display_url'],
                        'delete_url': data['delete_url'],
                        'thumb': {'url': data['thumb']['url']},
                        'medium': data['medium']['url'],
                        'size': data['size'],
                        'expiration': data.get('expiration'),
                        'filename': data['image']['filename'],
                        'service': 'imgbb'
                    }
                else:
                    error = result.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"❌ Upload failed: {error}")
                    return None
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ Upload timeout (>60s)")
            return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_image(self, image_path: str, title: Optional[str] = None, 
                    expiration: int = 0) -> Optional[Dict[str, str]]:
        """
        Upload image to ImgBB
        
        Args:
            image_path: Path to image file
            title: Optional image title
            expiration: Auto-delete after seconds (0 = never, max 15552000 = 180 days)
            
        Returns:
            Dict with URLs or None if failed
            
        Example:
            >>> uploader = ImgBBUploader()
            >>> result = uploader.upload_image("test.png")
            >>> print(result['url'])
            https://i.ibb.co/abc123/test.png
        """
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                logger.error(f"❌ Image not found: {image_path}")
                return None
            
            # Validate file
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            if image_path.suffix.lower() not in valid_extensions:
                logger.error(f"❌ Invalid image format: {image_path.suffix}")
                return None
            
            logger.info(f"📤 Uploading {image_path.name} to ImgBB...")
            
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare payload
            payload = {
                'key': self.api_key,
                'image': image_data,
                'name': title or image_path.stem,
            }
            
            if expiration > 0:
                payload['expiration'] = min(expiration, 15552000)
            
            response = requests.post(
                self.API_URL,
                data=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    data = result['data']
                    
                    logger.info(f"✅ Upload successful!")
                    logger.info(f"🔗 URL: {data['url']}")
                    
                    return {
                        'url': data['url'],
                        'display_url': data['display_url'],
                        'delete_url': data['delete_url'],
                        'thumbnail': data['thumb']['url'],
                        'medium': data['medium']['url'],
                        'size': data['size'],
                        'expiration': data.get('expiration'),
                        'filename': data['image']['filename'],
                        'service': 'imgbb'
                    }
                else:
                    error = result.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"❌ Upload failed: {error}")
                    return None
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ Upload timeout (>60s)")
            return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def delete_image(delete_url: str) -> bool:
        """Delete uploaded image"""
        try:
            if not delete_url:
                return False
                
            response = requests.get(delete_url, timeout=10)
            return response.status_code == 200
        except:
            return False


# Quick helper
def upload_to_imgbb(image_path: str, title: Optional[str] = None) -> Optional[str]:
    """Quick upload to ImgBB and return URL"""
    try:
        uploader = ImgBBUploader()
        result = uploader.upload_image(image_path, title)
        return result['url'] if result else None
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None


# Test script
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("ImgBB Uploader - Test Script")
        print("="*60)
        print("\nSetup:")
        print("1. Get API key: https://api.imgbb.com/")
        print("2. Add to .env: IMGBB_API_KEY=your_key")
        print("\nUsage: python imgbb_uploader.py <image_path>")
        print("Example: python imgbb_uploader.py test.png\n")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("\n" + "="*60)
    print("🧪 TESTING IMGBB UPLOAD")
    print("="*60)
    print(f"📁 File: {image_path}\n")
    
    try:
        uploader = ImgBBUploader()
        result = uploader.upload_image(image_path)
        
        if result:
            print("\n" + "="*60)
            print("✅ UPLOAD SUCCESS!")
            print("="*60)
            print(f"🔗 Image URL:   {result['url']}")
            print(f"📱 Display URL: {result['display_url']}")
            print(f"🗑️  Delete URL:  {result['delete_url']}")
            print(f"🖼️  Thumbnail:   {result['thumbnail']}")
            print(f"📦 Size:        {result['size']:,} bytes")
            print("="*60 + "\n")
        else:
            print("\n❌ Upload failed!\n")
            sys.exit(1)
    except ValueError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)
