"""
Firebase Configuration for AI-Assistant
Auto data sampling to keep services active

NOTE: API keys are loaded from environment variables (.env file)
Never commit API keys directly in code!
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Firebase Web Configuration - loaded from environment variables
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY", ""),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
    "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
    "appId": os.getenv("FIREBASE_APP_ID", ""),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID", "")
}

# Firebase domains
FIREBASE_DOMAINS = [
    "ai-assistant-7dbb8.web.app",
    "ai-assistant-7dbb8.firebaseapp.com"
]

def get_firebase_config():
    """Get Firebase configuration"""
    return FIREBASE_CONFIG

def get_firebase_script_tag():
    """Generate Firebase script tag for HTML"""
    return f'''
<script type="module">
  import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/12.8.0/firebase-app.js";
  import {{ getAnalytics }} from "https://www.gstatic.com/firebasejs/12.8.0/firebase-analytics.js";
  import {{ getFirestore, collection, addDoc, serverTimestamp }} from "https://www.gstatic.com/firebasejs/12.8.0/firebase-firestore.js";
  
  const firebaseConfig = {json.dumps(FIREBASE_CONFIG, indent=4)};
  
  const app = initializeApp(firebaseConfig);
  const analytics = getAnalytics(app);
  const db = getFirestore(app);
  
  // Auto log page view
  window.firebaseApp = app;
  window.firebaseDb = db;
  
  // Function to log events to Firestore
  window.logToFirebase = async function(collectionName, data) {{
    try {{
      const docRef = await addDoc(collection(db, collectionName), {{
        ...data,
        timestamp: serverTimestamp(),
        userAgent: navigator.userAgent,
        url: window.location.href
      }});
      console.log("Document written with ID: ", docRef.id);
      return docRef.id;
    }} catch (e) {{
      console.error("Error adding document: ", e);
      return null;
    }}
  }};
  
  // Log page view on load
  window.addEventListener('load', () => {{
    window.logToFirebase('page_views', {{
      page: window.location.pathname,
      referrer: document.referrer
    }});
  }});
</script>
'''
