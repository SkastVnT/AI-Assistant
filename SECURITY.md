# Security Policy

## 🔒 Overview

This document provides a comprehensive security guide for the AI-Assistant platform. We take security seriously and have implemented multiple layers of protection across all services.

## 📊 Current Security Status

**Last Security Audit:** February 2, 2026  
**Security Scan Results:** 120 findings identified (16 HIGH, 104 MEDIUM)  
**Status:** Active remediation in progress

### Quick Stats
- ✅ Security scanning enabled (Bandit, CodeQL, Dependency Review)
- ✅ Automated dependency updates (Dependabot)
- ✅ Input validation and sanitization modules
- ✅ API key management system
- ⚠️ 16 HIGH severity issues requiring attention
- ⚠️ 104 MEDIUM severity issues under review

## 🚨 Reporting Security Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

### DO NOT:
- ❌ Open public GitHub issues for security vulnerabilities
- ❌ Discuss vulnerabilities publicly before they are fixed
- ❌ Exploit vulnerabilities for testing without permission

### DO:
1. ✅ Email security concerns to: **nguyvip007@gmail.com**
2. ✅ Include detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)
3. ✅ Wait for acknowledgment (we aim to respond within 48 hours)
4. ✅ Allow reasonable time for a fix before public disclosure

### Response Timeline
- **Initial Response:** Within 48 hours
- **Assessment:** Within 7 days
- **Fix Timeline:** Based on severity
  - Critical: 24-48 hours
  - High: 1-2 weeks
  - Medium: 2-4 weeks
  - Low: Next scheduled release

## 🔍 Known Security Issues

### HIGH Severity Issues (16 Total)

#### 1. Weak Hash Functions (8 occurrences)
**Issue:** Use of MD5 hash function for security-sensitive operations  
**Risk:** MD5 is cryptographically broken and should not be used for security  
**Status:** Under review  
**Recommendation:** Migrate to SHA-256 or better

**Affected Files:**
- `services/chatbot/app/controllers/chat_controller.py`
- `services/text2sql/app/utils/cache_helper.py`
- And 6 other locations

**Temporary Mitigation:**
```python
# Instead of:
hashlib.md5(data.encode()).hexdigest()

# Use:
hashlib.sha256(data.encode()).hexdigest()
# Or for non-security uses:
hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()
```

#### 2. Flask Debug Mode Enabled (5 occurrences)
**Issue:** Flask applications running with `debug=True` in production  
**Risk:** Exposes Werkzeug debugger allowing arbitrary code execution  
**Status:** Critical - Requires immediate attention  
**Recommendation:** Ensure `debug=False` in production deployments

**Affected Files:**
- `services/speech2text/app/tools/web_ui.py`
- `services/document-intelligence/app/main.py`
- And 3 other locations

**Fix Required:**
```python
# Production settings
app.run(host='0.0.0.0', port=5000, debug=False)

# Or use environment variable
app.run(host='0.0.0.0', port=5000, debug=os.getenv('DEBUG', 'False') == 'True')
```

#### 3. Shell Injection Vulnerabilities (3 occurrences)
**Issue:** Use of `shell=True` in subprocess calls  
**Risk:** Potential command injection if user input is included  
**Status:** Under review  
**Recommendation:** Avoid `shell=True` or carefully sanitize inputs

**Affected Files:**
- `scripts/deploy_public.py`
- `scripts/utilities/system_check.py`
- `services/hub-gateway/utils/process_manager.py`

**Secure Alternative:**
```python
# Instead of:
subprocess.Popen(f"command {user_input}", shell=True)

# Use:
subprocess.Popen(["command", user_input], shell=False)
```

### MEDIUM Severity Issues (104 Total)

#### 4. Unsafe Model Downloads (65 occurrences)
**Issue:** Hugging Face model downloads without revision pinning  
**Risk:** Potentially malicious model versions could be downloaded  
**Status:** Monitoring  
**Recommendation:** Pin model revisions in production

**Example Fix:**
```python
# Pin specific revision
model = AutoModel.from_pretrained(
    "model-name",
    revision="abc123def456"  # Pin specific commit
)
```

#### 5. Binding to All Interfaces (24 occurrences)
**Issue:** Services binding to 0.0.0.0 without firewall restrictions  
**Risk:** Services exposed to network without access control  
**Status:** Expected behavior for containerized services  
**Recommendation:** Ensure proper network security and firewalls

#### 6. Unsafe PyTorch Load (7 occurrences)
**Issue:** Using `torch.load()` without weights_only parameter  
**Risk:** Can execute arbitrary code from malicious checkpoint files  
**Status:** Under review  
**Recommendation:** Use `weights_only=True` for untrusted sources

**Secure Usage:**
```python
# For loading from untrusted sources
torch.load(path, weights_only=True)

# Or for trusted internal checkpoints
torch.load(path, weights_only=False)  # Only if you control the file
```

#### 7. Use of exec() (3 occurrences)
**Issue:** Dynamic code execution using `exec()`  
**Risk:** Arbitrary code execution if user input reaches exec  
**Status:** Under review  
**Recommendation:** Use safer alternatives or strict input validation

**Affected Files:**
- `scripts/fix_dependencies.py`
- `services/chatbot/src/sandbox/code_executor.py`

#### 8. Eval Usage (3 occurrences)
**Issue:** Use of `eval()` for parsing expressions  
**Risk:** Code injection if user input is evaluated  
**Status:** Under review  
**Recommendation:** Use `ast.literal_eval()` for safe evaluation

#### 9. Pickle Deserialization (1 occurrence)
**Issue:** Unpickling untrusted data  
**Risk:** Arbitrary code execution via malicious pickle files  
**Status:** Under review  
**Location:** `services/hub-gateway/utils/google_drive_uploader.py`

#### 10. SQL Injection Risk (1 occurrence)
**Issue:** String-based SQL query construction  
**Risk:** SQL injection if user input is concatenated  
**Status:** Under review  
**Location:** `services/mcp-server/tools/advanced_tools.py`

**Fix Required:**
```python
# Use parameterized queries
cursor.execute("SELECT * FROM table WHERE id = ?", (user_id,))
```

## 🛡️ Security Best Practices

### For Contributors

#### 1. API Keys and Secrets
- ✅ Never commit API keys, tokens, or credentials to git
- ✅ Use `.env` files (already in `.gitignore`)
- ✅ Use `.env.example` as a template
- ✅ Rotate keys immediately if accidentally exposed

**Environment Variables:**
```bash
# Copy template
cp .env.example .env

# Edit with your keys
# .env is automatically ignored by git
```

#### 2. Input Validation
Always validate and sanitize user input using our security modules:

```python
from src.security.input_validator import InputValidator
from src.security.sanitizer import Sanitizer

validator = InputValidator()
sanitizer = Sanitizer()

# Validate input
schema = {
    'username': {'type': str, 'min_length': 3, 'max_length': 20},
    'email': {'type': str, 'pattern': 'email'}
}
result = validator.validate(user_data, schema)

if not result.is_valid:
    return {"error": result.errors}

# Sanitize before use
clean_data = sanitizer.sanitize_dict(user_data)
```

#### 3. SQL Injection Prevention
- ✅ Use parameterized queries (prepared statements)
- ✅ Never concatenate user input into SQL
- ✅ Use ORM frameworks when possible (SQLAlchemy, etc.)

```python
# ✅ GOOD - Parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ❌ BAD - String concatenation
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

#### 4. Command Injection Prevention
- ✅ Avoid `shell=True` in subprocess calls
- ✅ Use list arguments instead of strings
- ✅ Validate and sanitize all inputs

```python
# ✅ GOOD
subprocess.run(["command", arg1, arg2], shell=False)

# ❌ BAD
subprocess.run(f"command {arg1} {arg2}", shell=True)
```

#### 5. File Upload Security
- ✅ Validate file types and extensions
- ✅ Limit file sizes
- ✅ Scan uploads for malware
- ✅ Store uploads outside webroot
- ✅ Use random filenames to prevent path traversal

```python
from src.security.input_validator import InputValidator

validator = InputValidator()

# Validate filename
if not validator.validate_filename(filename):
    raise ValueError("Invalid filename")

# Sanitize path
safe_path = sanitizer.sanitize_path(upload_path, base_dir="/app/uploads")
```

#### 6. XSS Prevention
- ✅ Escape all user-generated content in HTML
- ✅ Use Content Security Policy (CSP) headers
- ✅ Sanitize rich text inputs

```python
from src.security.sanitizer import sanitize

# Sanitize before rendering
safe_content = sanitize(user_content)
```

#### 7. Authentication & Authorization
- ✅ Use API key validation for service access
- ✅ Implement rate limiting (already configured)
- ✅ Log authentication attempts
- ✅ Use secure session management

```python
from src.security.api_key_manager import APIKeyManager

manager = APIKeyManager()

# Generate key for new service
api_key = manager.generate_key("service-name")

# Validate incoming requests
metadata = manager.validate_key(request_api_key)
if not metadata:
    return {"error": "Invalid API key"}, 401
```

#### 8. Dependency Management
- ✅ Keep dependencies updated (Dependabot enabled)
- ✅ Review security advisories weekly
- ✅ Pin dependency versions in production
- ✅ Use virtual environments

```bash
# Check for vulnerabilities
pip-audit -r requirements.txt

# Update dependencies
pip install --upgrade package-name
```

#### 9. Secure Configuration
- ✅ Disable debug mode in production
- ✅ Use HTTPS in production
- ✅ Set secure cookie flags
- ✅ Configure CORS properly

```python
# Flask security headers
from flask_cors import CORS

app = Flask(__name__)
app.config['DEBUG'] = False
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app, origins=["https://yourdomain.com"])
```

#### 10. Logging & Monitoring
- ✅ Log security events
- ✅ Monitor for suspicious activity
- ✅ Set up alerts for critical issues
- ✅ Never log sensitive data (passwords, tokens)

```python
import logging

# Configure secure logging
logger = logging.getLogger(__name__)

# Log security events
logger.warning(f"Failed login attempt from IP: {ip_address}")

# ❌ Never log sensitive data
# logger.info(f"User password: {password}")  # BAD!
```

## 🔐 Security Modules

The platform includes several security modules in `src/security/`:

### 1. API Key Manager (`api_key_manager.py`)
Manages API keys for service authentication.

**Features:**
- Key generation with custom prefixes
- Key validation and revocation
- Key rotation
- Expiration support
- Usage statistics

**Usage:**
```python
from src.security.api_key_manager import APIKeyManager

manager = APIKeyManager(key_prefix="myapp_")

# Generate new key
key = manager.generate_key("service-name", expires_in=30)  # 30 days

# Validate key
metadata = manager.validate_key(key)

# Rotate key
new_key = manager.rotate_key(old_key)

# Revoke key
manager.revoke_key(key)
```

### 2. Input Validator (`input_validator.py`)
Validates user input against schemas.

**Features:**
- Required field validation
- Type checking
- Length limits
- Pattern matching (email, URL, alphanumeric, etc.)
- Custom validators
- Number range validation

**Usage:**
```python
from src.security.input_validator import InputValidator

validator = InputValidator()

schema = {
    'username': {
        'required': True,
        'type': str,
        'min_length': 3,
        'max_length': 20,
        'pattern': 'alphanumeric'
    },
    'email': {
        'required': True,
        'type': str,
        'pattern': 'email'
    },
    'age': {
        'type': int,
        'min': 0,
        'max': 120
    }
}

result = validator.validate(user_data, schema)
if not result.is_valid:
    return {"errors": result.errors}
```

### 3. Sanitizer (`sanitizer.py`)
Sanitizes user input to prevent injection attacks.

**Features:**
- HTML/XSS sanitization
- SQL input sanitization
- Filename sanitization
- Path traversal prevention
- Length limiting
- Recursive sanitization (dicts, lists)

**Usage:**
```python
from src.security.sanitizer import Sanitizer, sanitize

sanitizer = Sanitizer(max_length=1000)

# Sanitize string
clean = sanitizer.sanitize_string("<script>alert('xss')</script>")

# Sanitize dictionary
clean_data = sanitizer.sanitize_dict(user_data)

# Sanitize filename
safe_filename = sanitizer.sanitize_filename("../../etc/passwd")

# Sanitize path
safe_path = sanitizer.sanitize_path(user_path, "/app/uploads")

# Quick sanitization
clean = sanitize("<b>Bold text</b>")
```

## 🚀 Deployment Security

### Docker Security
```yaml
# docker-compose.yml security best practices
services:
  app:
    # Run as non-root user
    user: "1000:1000"
    
    # Read-only root filesystem
    read_only: true
    
    # Drop unnecessary capabilities
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    
    # Resource limits
    mem_limit: 2g
    cpus: 1.0
    
    # Security options
    security_opt:
      - no-new-privileges:true
```

### Network Security
- ✅ Use reverse proxy (nginx) for SSL termination
- ✅ Configure firewall rules
- ✅ Implement rate limiting
- ✅ Use VPN for internal service communication
- ✅ Enable fail2ban for brute force protection

### Environment Security
```bash
# Set secure file permissions
chmod 600 .env
chmod 700 scripts/*.sh

# Restrict service user permissions
useradd -r -s /bin/false aiassistant
chown -R aiassistant:aiassistant /app
```

## 📋 Security Checklist for New Features

Before submitting a PR, ensure:

- [ ] All user inputs are validated
- [ ] All user inputs are sanitized
- [ ] No secrets committed to git
- [ ] SQL queries use parameterization
- [ ] Shell commands avoid `shell=True`
- [ ] File uploads are validated
- [ ] Authentication is required where appropriate
- [ ] Rate limiting is configured
- [ ] Error messages don't leak sensitive info
- [ ] Dependencies are up to date
- [ ] Security tests pass
- [ ] Debug mode is disabled
- [ ] Logging doesn't include sensitive data

## 🔬 Testing Security

Run security tests:
```bash
# Unit tests including security tests
pytest tests/unit/test_security.py -v

# Run Bandit security linter
python -m bandit -r . --exclude ./venv*,./ComfyUI,**/tests/** -f json -o security-report.json

# Check dependencies
pip-audit -r requirements.txt

# Run all tests
pytest tests/ -v
```

## 📚 Additional Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Flask Security](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Docker Security](https://docs.docker.com/engine/security/)

### Security Tools Used
- **Bandit:** Python security linter
- **CodeQL:** Semantic code analysis
- **Dependabot:** Automated dependency updates
- **pip-audit:** PyPI package vulnerability scanner
- **Safety:** Dependency vulnerability checker

### Internal Documentation
- `services/image-upscale/SECURITY_ENV.md` - Environment security guide
- `tests/unit/test_security.py` - Security test suite
- `src/security/` - Security module implementations

## 📞 Contact

For security concerns or questions:
- **Email:** nguyvip007@gmail.com
- **GitHub Issues:** For non-security bugs only
- **Discord:** https://discord.gg/d3K8Ck9NeR (For general questions)

## 📝 Version History

### v2.0.0 (Current)
- Comprehensive security documentation added
- Security audit completed (120 findings)
- Security modules implemented (API key manager, validator, sanitizer)
- CodeQL and dependency scanning enabled
- 16 HIGH and 104 MEDIUM issues identified and documented

### Previous Versions
- v1.x: Basic security measures
- Initial release: No formal security policy

---

**Last Updated:** February 2, 2026  
**Maintained By:** SkastVnT  
**Security Point of Contact:** nguyvip007@gmail.com

---

## 🔒 Commitment

We are committed to:
1. ✅ Maintaining high security standards
2. ✅ Responding promptly to security reports
3. ✅ Keeping dependencies up to date
4. ✅ Regular security audits
5. ✅ Transparent communication about security issues

**⭐ If you find this security policy helpful, please star our repository!**
