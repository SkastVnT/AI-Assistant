"""
Firebase Authentication Routes
Supports Email/Password and Google Sign-In
"""
import os
import sys
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, render_template_string
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import logger

auth_bp = Blueprint('auth', __name__)

# Firebase Admin SDK (optional for server-side verification)
firebase_auth = None
try:
    import firebase_admin
    from firebase_admin import auth as fb_auth
    
    FIREBASE_CREDS_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', '')
    if FIREBASE_CREDS_PATH and os.path.exists(FIREBASE_CREDS_PATH):
        if not firebase_admin._apps:
            cred = firebase_admin.credentials.Certificate(FIREBASE_CREDS_PATH)
            firebase_admin.initialize_app(cred)
        firebase_auth = fb_auth
        logger.info("[Auth] Firebase Admin SDK initialized")
except Exception as e:
    logger.warning(f"[Auth] Firebase Admin SDK not available: {e}")


@auth_bp.route('/api/auth/config', methods=['GET'])
def get_auth_config():
    """Get Firebase configuration for frontend"""
    try:
        from config.firebase_config import get_firebase_config
        config = get_firebase_config()
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"[Auth] Config error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/auth/verify', methods=['POST'])
def verify_token():
    """Verify Firebase ID token"""
    try:
        data = request.json
        id_token = data.get('idToken')
        
        if not id_token:
            return jsonify({'error': 'No token provided'}), 400
        
        if not firebase_auth:
            # If Firebase Admin is not configured, accept token as-is
            # Frontend should handle authentication
            return jsonify({
                'success': True,
                'message': 'Token accepted (server-side verification disabled)',
                'verified': False
            })
        
        # Verify the ID token
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        name = decoded_token.get('name', '')
        
        logger.info(f"[Auth] Token verified for user: {uid}")
        
        return jsonify({
            'success': True,
            'verified': True,
            'user': {
                'uid': uid,
                'email': email,
                'name': name
            }
        })
        
    except Exception as e:
        logger.error(f"[Auth] Verification error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 401


@auth_bp.route('/api/auth/user', methods=['GET'])
def get_user():
    """Get user info from token (header: Authorization: Bearer <token>)"""
    try:
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No token provided'}), 401
        
        id_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        if not firebase_auth:
            return jsonify({
                'success': False,
                'error': 'Server-side authentication not configured'
            }), 500
        
        decoded_token = firebase_auth.verify_id_token(id_token)
        
        return jsonify({
            'success': True,
            'user': {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', ''),
                'name': decoded_token.get('name', ''),
                'picture': decoded_token.get('picture', '')
            }
        })
        
    except Exception as e:
        logger.error(f"[Auth] Get user error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 401


@auth_bp.route('/login')
def login_page():
    """Render login page with Firebase Auth"""
    try:
        from config.firebase_config import get_firebase_config
        config = get_firebase_config()
        
        return render_template_string(LOGIN_TEMPLATE, firebase_config=json.dumps(config))
    except Exception as e:
        logger.error(f"[Auth] Login page error: {e}")
        return f"Error: {e}", 500


# Login page template with Firebase Auth
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - AI Assistant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo h1 { color: #fff; font-size: 28px; }
        .logo span { color: #e94560; }
        .form-group { margin-bottom: 20px; }
        .form-group label {
            display: block;
            color: #ccc;
            margin-bottom: 8px;
            font-size: 14px;
        }
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 16px;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #e94560;
            background: rgba(255, 255, 255, 0.1);
        }
        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 12px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #e94560 0%, #f72585 100%);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(233, 69, 96, 0.4); }
        .btn-google {
            background: #fff;
            color: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .btn-google:hover { background: #f5f5f5; }
        .divider {
            text-align: center;
            color: #666;
            margin: 20px 0;
            position: relative;
        }
        .divider::before, .divider::after {
            content: '';
            position: absolute;
            top: 50%;
            width: 40%;
            height: 1px;
            background: rgba(255, 255, 255, 0.1);
        }
        .divider::before { left: 0; }
        .divider::after { right: 0; }
        .error-message {
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid rgba(255, 0, 0, 0.3);
            color: #ff6b6b;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .success-message {
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid rgba(0, 255, 0, 0.3);
            color: #6bff6b;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .toggle-form {
            text-align: center;
            margin-top: 20px;
            color: #999;
        }
        .toggle-form a { color: #e94560; text-decoration: none; }
        .toggle-form a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>🤖 AI <span>Assistant</span></h1>
        </div>
        
        <div id="error-message" class="error-message"></div>
        <div id="success-message" class="success-message"></div>
        
        <form id="login-form">
            <div class="form-group">
                <label for="email">Email</label>
                <input type="email" id="email" placeholder="Enter your email" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="btn btn-primary" id="submit-btn">Sign In</button>
        </form>
        
        <div class="divider">or</div>
        
        <button class="btn btn-google" id="google-btn">
            <svg width="20" height="20" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign in with Google
        </button>
        
        <div class="toggle-form" id="toggle-container">
            Don't have an account? <a href="#" id="toggle-link">Sign up</a>
        </div>
    </div>

    <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
        import { 
            getAuth, 
            signInWithEmailAndPassword, 
            createUserWithEmailAndPassword,
            signInWithPopup, 
            GoogleAuthProvider 
        } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";
        
        const firebaseConfig = {{ firebase_config|safe }};
        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        const googleProvider = new GoogleAuthProvider();
        
        let isSignUp = false;
        const form = document.getElementById('login-form');
        const submitBtn = document.getElementById('submit-btn');
        const toggleLink = document.getElementById('toggle-link');
        const toggleContainer = document.getElementById('toggle-container');
        const errorDiv = document.getElementById('error-message');
        const successDiv = document.getElementById('success-message');
        
        function showError(msg) {
            errorDiv.textContent = msg;
            errorDiv.style.display = 'block';
            successDiv.style.display = 'none';
        }
        
        function showSuccess(msg) {
            successDiv.textContent = msg;
            successDiv.style.display = 'block';
            errorDiv.style.display = 'none';
        }
        
        function onSuccess(user) {
            showSuccess('Login successful! Redirecting...');
            // Store user info
            localStorage.setItem('user', JSON.stringify({
                uid: user.uid,
                email: user.email,
                displayName: user.displayName,
                photoURL: user.photoURL
            }));
            // Get ID token for API calls
            user.getIdToken().then(token => {
                localStorage.setItem('authToken', token);
                // Redirect to main app
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            });
        }
        
        // Toggle between sign in and sign up
        toggleLink.addEventListener('click', (e) => {
            e.preventDefault();
            isSignUp = !isSignUp;
            submitBtn.textContent = isSignUp ? 'Sign Up' : 'Sign In';
            toggleLink.textContent = isSignUp ? 'Sign in' : 'Sign up';
            toggleContainer.innerHTML = isSignUp 
                ? 'Already have an account? <a href="#" id="toggle-link">Sign in</a>'
                : 'Don\\'t have an account? <a href="#" id="toggle-link">Sign up</a>';
            document.getElementById('toggle-link').addEventListener('click', arguments.callee);
        });
        
        // Email/Password auth
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                let result;
                if (isSignUp) {
                    result = await createUserWithEmailAndPassword(auth, email, password);
                } else {
                    result = await signInWithEmailAndPassword(auth, email, password);
                }
                onSuccess(result.user);
            } catch (error) {
                showError(error.message);
            }
        });
        
        // Google auth
        document.getElementById('google-btn').addEventListener('click', async () => {
            try {
                const result = await signInWithPopup(auth, googleProvider);
                onSuccess(result.user);
            } catch (error) {
                showError(error.message);
            }
        });
    </script>
</body>
</html>
'''
