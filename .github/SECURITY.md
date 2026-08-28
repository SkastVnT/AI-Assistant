# Security Policy

## 🔒 Overview

This document provides a comprehensive security guide for the AI-Assistant platform. We take security seriously and have implemented multiple layers of protection across all services.

## 📊 Current Security Status

**Last Security Audit:** June 17, 2026 (full re-audit — 22 audit items)  
**Previous Audit:** February 2, 2026 (120 findings: 16 HIGH, 104 MEDIUM)  
**Current Status:** ✅ All HIGH and MEDIUM findings resolved or verified false positive

### Quick Stats

- ✅ Security scanning enabled (Bandit, CodeQL, Dependency Review, Trivy)
- ✅ Automated dependency updates (Dependabot)
- ✅ Input validation and sanitization modules
- ✅ API key management system
- ✅ All 16 original HIGH severity issues resolved
- ✅ All 104 original MEDIUM issues resolved or verified false positive
- ⚠️ 1 CVE with no fix available: torch GHSA-rrmf-rvhw-rf47 (torch.jit.script, no fix upstream)
- ⚠️ protobuf CVEs (GHSA-8qvm-5x2c-j2w7, GHSA-7gcm-g887-7qv7): requirements already pin ≥7.35.0 (fixed)

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
**Status:** ✅ Resolved

- `services/chatbot/src/utils/conversation_manager.py` — replaced with `secrets.token_hex()` (cryptographically secure ID generation)
- `app/image_pipeline/anime_pipeline/saa_character_db.py` — added `usedforsecurity=False` (non-security: thumbnail key lookup in external JSON)
- `app/src/cache/redis_cache.py` — added `usedforsecurity=False` (non-security: cache key generation)
- Remaining occurrences are in vendored code excluded via `pyproject.toml`

#### 2. Flask Debug Mode Enabled (5 occurrences)
**Issue:** Flask applications running with `debug=True` in production  
**Risk:** Exposes Werkzeug debugger allowing arbitrary code execution  
**Status:** ✅ Resolved

- `services/chatbot/app/config.py` — default config changed from `DevelopmentConfig` → `ProductionConfig`
- `app/config/model_config.py` — `DEBUG` default changed from `"True"` → `"False"`
- Remaining occurrences are in archived/vendored services not deployed

#### 3. Shell Injection Vulnerabilities (3 occurrences)
**Issue:** Use of `shell=True` in subprocess calls with f-string arguments  
**Risk:** Potential command injection if user input is included  
**Status:** ✅ Resolved

- `app/scripts/deploy_public.py` — `kill_port()` rewritten to use list args `["lsof", "-ti", f":{int(port)}"]`
- `app/scripts/utilities/service_health_checker.py` — replaced with `shlex.split(test_command)` and list form for pip install
- `app/scripts/expose_services.sh` — cloudflared binary download pinned to version `2025.5.0` with `curl -fsSL`; Python inline code injection pattern fixed to use `sys.argv` argument passing

### MEDIUM Severity Issues (104 Total)

#### 4. Unsafe Model Downloads (65 occurrences)
**Issue:** Hugging Face model downloads without revision pinning  
**Risk:** Potentially malicious model versions could be downloaded  
**Status:** ✅ Resolved — zero occurrences in first-party code. `services/chatbot/src/utils/local_model_loader.py` uses `local_files_only=True` (no remote downloads at runtime). All 65 occurrences are in vendored code (ComfyUI custom nodes, stable-diffusion repositories) excluded via `pyproject.toml`.

#### 5. Binding to All Interfaces (24 occurrences)
**Issue:** Services binding to 0.0.0.0 without firewall restrictions  
**Risk:** Services exposed to network without access control  
**Status:** ✅ Resolved — intentional for containerized microservices (Docker networking provides isolation). All first-party occurrences annotated with `# nosec B104`. Remaining occurrences are in vendored ComfyUI code. Additional fix: `app/config/model_config.py` DEBUG default changed from `"True"` to `"False"`.

#### 6. Unsafe PyTorch Load (7 occurrences)
**Issue:** Using `torch.load()` without weights_only parameter  
**Risk:** Can execute arbitrary code from malicious checkpoint files  
**Status:** ✅ Resolved — all occurrences are in vendored third-party libraries (taming-transformers, stable-diffusion repositories, ComfyUI custom nodes). Zero occurrences in first-party code (`app/`, `services/chatbot/`, `services/mcp-server/`). Bandit exclude config added via `pyproject.toml` to suppress vendored-code false positives.

#### 7. Use of exec() (3 occurrences)
**Issue:** Dynamic code execution using `exec()`  
**Risk:** Arbitrary code execution if user input reaches exec  
**Status:** ✅ Resolved — `app/scripts/fix_dependencies.py` contains no exec/eval (stale finding). `services/chatbot/src/sandbox/code_executor.py` no longer exists (deleted). Remaining occurrences are in vendored repos (CodeFormer setup.py — standard version-read pattern).  
**Affected Files (all vendored):**

- `services/stable-diffusion/repositories/CodeFormer/basicsr/setup.py` — standard `exec(compile(...))` for `__version__` read

#### 8. Eval Usage (3 occurrences)
**Issue:** Use of `eval()` for parsing expressions  
**Risk:** Code injection if user input is evaluated  
**Status:** ✅ Resolved — no `eval()` calls found in first-party code (`app/`, `services/chatbot/`, `services/mcp-server/`). All occurrences are in vendored libraries excluded via `pyproject.toml`.

#### 9. Pickle Deserialization (1 occurrence)
**Issue:** Unpickling untrusted data  
**Risk:** Arbitrary code execution via malicious pickle files  
**Status:** ✅ Resolved — located in `private copy/archived-services/hub-gateway/utils/google_drive_uploader.py` (archived, not deployed). Pattern is standard Google OAuth token loading (`token.pickle`) from a developer-controlled path, not user input.

#### 10. SQL Injection Risk (1 occurrence)
**Issue:** String-based SQL query construction  
**Risk:** SQL injection if user input is concatenated  
**Status:** ✅ Resolved — `services/mcp-server/tools/advanced_tools.py` already uses parameterized queries (`cursor.execute(query, params)`), has `validate_select_only()` guard (SELECT-only, blocks semicolons), and table name validation (`isalnum()` check). `memory_manager.py` uses `?` placeholders with dynamically-built WHERE clauses. All f-string SQL has `# nosec B608` with justification. Bandit B608 false positive.

### June 2026 Audit — New Findings & Fixes

#### 11. Dockerfile Non-Root User Missing

**Status:** ✅ Resolved — Added `useradd -u 1001 appuser` + `USER appuser` + `--chown` to `app/rag/apps/api/Dockerfile` and `app/rag/apps/worker/Dockerfile`. `services/chatbot/Dockerfile` already had non-root user.

#### 12. API Key Middleware Fails Open

**Status:** ✅ Resolved — `services/chatbot/app/middleware/auth.py` `require_api_key()` previously allowed any non-empty key when `API_KEY` env var was not set. Fixed to fail closed: rejects all requests when `API_KEY` is not configured.

#### 13. CORS Hardcoded Wildcard

**Status:** ✅ Resolved — Both `services/chatbot/app/main.py` and `app/rag/apps/api/main.py` hardcoded `origins="*"`. Changed to read from `CORS_ORIGINS` env var (defaults to `"*"` for backward compatibility). Set `CORS_ORIGINS=https://yourdomain.com` in production.

#### 14. Bandit Config Format Error

**Status:** ✅ Resolved — `pyproject.toml` config file was in INI format; `--configfile` requires YAML. Converted to YAML format (`exclude_dirs` list). CI `ci-cd.yml` updated to pass `--configfile .bandit` so vendor exclusions apply consistently.

#### 15. Dependency CVEs (pip-audit)

| Package | CVE | Severity | Status |
| --- | --- | --- | --- |
| protobuf 3.20.x | GHSA-8qvm-5x2c-j2w7 | MEDIUM | ✅ Requirements pin ≥7.35.0 — run `pip install -r` to sync venv |
| protobuf 3.20.x | GHSA-7gcm-g887-7qv7 | MEDIUM | ✅ Same as above |
| torch | GHSA-rrmf-rvhw-rf47 | CRITICAL | ⚠️ No upstream fix. `torch.jit.script` memory corruption — not called by app code directly. Monitor upstream. |

#### 16. Shell Script Unsafe Binary Download

**Status:** ✅ Resolved — `app/scripts/expose_services.sh` downloaded cloudflared binary using `latest` URL without version pinning or `--fail` flag. Fixed to pin version `2025.5.0` with `curl -fsSL`.

#### 17. RAG Auth Backend Default

**Status:** ⚠️ Moved — the RAG service now lives in [rag-eval-gate](https://github.com/SkastVnT/rag-eval-gate); this item tracks there. `libs/auth/middleware.py` defaults to `AUTH_BACKEND=none` (trusts `x-tenant-id`/`x-user-id` headers without validation). Set `AUTH_BACKEND=api_key` in any production RAG deployment.

#### 18. Rate Limiting Scope

**Status:** ℹ️ Acceptable for current deployment — `services/chatbot/app/middleware/rate_limiter.py` is in-memory only (not distributed, not persistent across restarts). Sufficient for single-user desktop app. Would need Redis-backed limiter for multi-instance production deployment.

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
chmod 700 app/scripts/*.sh

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

### v3.0.0 (Current — June 17, 2026)

- Full re-audit: 22 audit items covering all first-party code
- All 16 HIGH and 104 MEDIUM issues from Feb 2026 audit resolved
- New findings fixed: Dockerfile hardening, API key fail-open, CORS wildcard, shell script injection, Bandit config
- pip-audit: protobuf CVEs resolved via requirements pinning; torch CVE has no upstream fix
- Bandit full scan: 0 HIGH remaining in first-party code (27,687 lines scanned)
- `pyproject.toml` YAML config added for consistent vendor exclusion across local and CI runs

### v2.0.0 (February 2, 2026)

- Comprehensive security documentation added
- Security audit completed (120 findings: 16 HIGH, 104 MEDIUM)
- Security modules implemented (API key manager, validator, sanitizer)
- CodeQL and dependency scanning enabled

### Previous Versions

- v1.x: Basic security measures
- Initial release: No formal security policy

---

**Last Updated:** June 17, 2026  
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
