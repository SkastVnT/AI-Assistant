"""
Image Storage Service
Upload images to ImgBB and save metadata to MongoDB/Firebase
"""
import os
import base64
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ImgBB API
IMGBB_API_KEY = os.getenv('IMGBB_API_KEY', '')
IMGBB_UPLOAD_URL = 'https://api.imgbb.com/1/upload'

# MongoDB (optional)
try:
    from pymongo import MongoClient
    MONGO_URI = os.getenv('MONGODB_URI', '')
    if MONGO_URI:
        mongo_client = MongoClient(
            MONGO_URI, 
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        mongo_db = mongo_client.get_default_database() or mongo_client['ai_assistant']
        images_collection = mongo_db['generated_images']
        logger.info("[ImageStorage] MongoDB connected")
    else:
        mongo_client = None
        images_collection = None
except Exception as e:
    logger.warning(f"[ImageStorage] MongoDB not available: {e}")
    mongo_client = None
    images_collection = None

# Firebase Admin (optional)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    FIREBASE_CREDS_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', '')
    if FIREBASE_CREDS_PATH and os.path.exists(FIREBASE_CREDS_PATH):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDS_PATH)
            firebase_admin.initialize_app(cred)
        firebase_db = firestore.client()
        logger.info("[ImageStorage] Firebase connected")
    else:
        firebase_db = None
except Exception as e:
    logger.warning(f"[ImageStorage] Firebase not available: {e}")
    firebase_db = None


def upload_to_imgbb(image_base64: str, name: str = None) -> Optional[str]:
    """
    Upload image to ImgBB and return the URL
    
    Args:
        image_base64: Base64 encoded image data
        name: Optional name for the image
        
    Returns:
        URL of uploaded image or None if failed
    """
    if not IMGBB_API_KEY:
        logger.warning("[ImgBB] No API key configured")
        return None
    
    try:
        # Remove data URL prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
        
        payload = {
            'key': IMGBB_API_KEY,
            'image': image_base64,
            'name': name or f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        response = requests.post(IMGBB_UPLOAD_URL, data=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                url = result['data']['url']
                logger.info(f"[ImgBB] Image uploaded: {url}")
                return url
            else:
                logger.error(f"[ImgBB] Upload failed: {result}")
        else:
            logger.error(f"[ImgBB] HTTP error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"[ImgBB] Exception: {e}")
    
    return None


def save_to_mongodb(image_data: Dict[str, Any]) -> Optional[str]:
    """
    Save image metadata to MongoDB
    
    Args:
        image_data: Dictionary with image metadata
        
    Returns:
        Document ID or None if failed
    """
    if not images_collection:
        logger.warning("[MongoDB] Not connected")
        return None
    
    try:
        image_data['created_at'] = datetime.utcnow()
        result = images_collection.insert_one(image_data)
        logger.info(f"[MongoDB] Image saved: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[MongoDB] Save error: {e}")
        return None


def save_to_firebase(image_data: Dict[str, Any]) -> Optional[str]:
    """
    Save image metadata to Firebase Firestore
    
    Args:
        image_data: Dictionary with image metadata
        
    Returns:
        Document ID or None if failed
    """
    if not firebase_db:
        logger.warning("[Firebase] Not connected")
        return None
    
    try:
        image_data['created_at'] = datetime.utcnow()
        doc_ref = firebase_db.collection('generated_images').add(image_data)
        doc_id = doc_ref[1].id
        logger.info(f"[Firebase] Image saved: {doc_id}")
        return doc_id
    except Exception as e:
        logger.error(f"[Firebase] Save error: {e}")
        return None


def store_generated_image(
    image_base64: str,
    prompt: str,
    negative_prompt: str = "",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Store generated image to ImgBB and save metadata to databases
    
    Args:
        image_base64: Base64 encoded image
        prompt: Generation prompt
        negative_prompt: Negative prompt
        metadata: Additional metadata
        
    Returns:
        Dictionary with storage results
    """
    result = {
        'success': False,
        'imgbb_url': None,
        'mongodb_id': None,
        'firebase_id': None
    }
    
    # Upload to ImgBB
    imgbb_url = upload_to_imgbb(image_base64)
    if imgbb_url:
        result['imgbb_url'] = imgbb_url
        result['success'] = True
    
    # Prepare metadata
    image_metadata = {
        'url': imgbb_url,
        'prompt': prompt,
        'negative_prompt': negative_prompt,
        'source': 'comfyui',
        **(metadata or {})
    }
    
    # Save to MongoDB
    if imgbb_url:
        mongo_id = save_to_mongodb(image_metadata.copy())
        if mongo_id:
            result['mongodb_id'] = mongo_id
    
    # Save to Firebase
    if imgbb_url:
        firebase_id = save_to_firebase(image_metadata.copy())
        if firebase_id:
            result['firebase_id'] = firebase_id
    
    logger.info(f"[ImageStorage] Storage result: {result}")
    return result


def get_images_from_cloud(limit: int = 50) -> list:
    """
    Get images from cloud storage (MongoDB or Firebase)
    
    Args:
        limit: Maximum number of images to return
        
    Returns:
        List of image metadata
    """
    images = []
    
    # Try MongoDB first
    if images_collection:
        try:
            cursor = images_collection.find().sort('created_at', -1).limit(limit)
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                images.append(doc)
            if images:
                return images
        except Exception as e:
            logger.error(f"[MongoDB] Query error: {e}")
    
    # Fallback to Firebase
    if firebase_db:
        try:
            docs = firebase_db.collection('generated_images')\
                .order_by('created_at', direction='DESCENDING')\
                .limit(limit)\
                .stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                images.append(data)
        except Exception as e:
            logger.error(f"[Firebase] Query error: {e}")
    
    return images
