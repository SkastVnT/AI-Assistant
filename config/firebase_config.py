"""
Firebase Configuration for AI-Assistant
Auto data sampling to keep services active
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Firebase Web Configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAHX8Kpx3ZCZswzg5wyWycRCOqnGWCOaiM",
    "authDomain": "ai-assistant-7dbb8.firebaseapp.com",
    "projectId": "ai-assistant-7dbb8",
    "storageBucket": "ai-assistant-7dbb8.firebasestorage.app",
    "messagingSenderId": "31625059118",
    "appId": "1:31625059118:web:b6327b08cea18f9be938bf",
    "measurementId": "G-G6EKFZHZPZ"
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
