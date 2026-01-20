"""
Auto Data Sampling for MongoDB and Firebase
Keeps databases active by sending 1 sample per day
"""
import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://thanhnguyen:avBlS2SMWBS0TXFu@ai-assistant.aspuqwb.mongodb.net/')

# Firebase Configuration  
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAHX8Kpx3ZCZswzg5wyWycRCOqnGWCOaiM",
    "projectId": "ai-assistant-7dbb8",
}

# Sampling interval (24 hours in seconds)
SAMPLE_INTERVAL = 24 * 60 * 60  # 86400 seconds

# Last sample tracking file
SAMPLE_TRACKING_FILE = Path(__file__).parent.parent / 'logs' / 'auto_sample_tracking.json'


def load_tracking():
    """Load tracking data"""
    if SAMPLE_TRACKING_FILE.exists():
        try:
            with open(SAMPLE_TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'last_mongodb_sample': None, 'last_firebase_sample': None}


def save_tracking(data):
    """Save tracking data"""
    SAMPLE_TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SAMPLE_TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def should_sample(last_sample_time):
    """Check if we should send a sample (once per day)"""
    if not last_sample_time:
        return True
    try:
        last_time = datetime.fromisoformat(last_sample_time)
        return datetime.now() - last_time > timedelta(hours=23)
    except:
        return True


def sample_mongodb():
    """Send a sample to MongoDB to keep it active"""
    try:
        from pymongo import MongoClient
        
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client.get_database('ai_assistant')
        
        # Insert health check sample
        sample = {
            'type': 'health_check',
            'service': 'ai-assistant',
            'timestamp': datetime.now().isoformat(),
            'status': 'active',
            'message': 'Daily auto-sample to keep database active'
        }
        
        result = db.health_checks.insert_one(sample)
        logger.info(f"✅ MongoDB sample sent: {result.inserted_id}")
        
        # Clean old samples (keep last 30)
        db.health_checks.delete_many({
            'type': 'health_check',
            '_id': {'$nin': list(db.health_checks.find({'type': 'health_check'}).sort('_id', -1).limit(30).distinct('_id'))}
        })
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB sample failed: {e}")
        return False


def sample_firebase():
    """Send a sample to Firebase to keep it active"""
    try:
        import requests
        
        # Use Firebase REST API
        firebase_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_CONFIG['projectId']}/databases/(default)/documents/health_checks"
        
        sample = {
            'fields': {
                'type': {'stringValue': 'health_check'},
                'service': {'stringValue': 'ai-assistant'},
                'timestamp': {'stringValue': datetime.now().isoformat()},
                'status': {'stringValue': 'active'},
                'message': {'stringValue': 'Daily auto-sample to keep database active'}
            }
        }
        
        response = requests.post(firebase_url, json=sample, timeout=10)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Firebase sample sent successfully")
            return True
        else:
            logger.warning(f"⚠️ Firebase sample response: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Firebase sample failed: {e}")
        return False


def run_auto_sampling():
    """Run auto sampling check"""
    tracking = load_tracking()
    
    # Check MongoDB
    if should_sample(tracking.get('last_mongodb_sample')):
        if sample_mongodb():
            tracking['last_mongodb_sample'] = datetime.now().isoformat()
            
    # Check Firebase
    if should_sample(tracking.get('last_firebase_sample')):
        if sample_firebase():
            tracking['last_firebase_sample'] = datetime.now().isoformat()
    
    save_tracking(tracking)
    return tracking


def start_background_sampling():
    """Start background sampling thread"""
    def sampling_loop():
        while True:
            try:
                run_auto_sampling()
            except Exception as e:
                logger.error(f"Auto sampling error: {e}")
            time.sleep(3600)  # Check every hour
    
    thread = threading.Thread(target=sampling_loop, daemon=True)
    thread.start()
    logger.info("🔄 Auto data sampling started (1 sample/day)")
    return thread


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Running auto sampling...")
    result = run_auto_sampling()
    print(f"Tracking: {json.dumps(result, indent=2)}")
