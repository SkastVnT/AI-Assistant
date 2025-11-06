# 🔒 Security Policy

## 📋 Supported Versions

The following table shows which versions of AI-Assistant are currently receiving security updates:

| Service | Version | Supported | Python | Status |
| ------- | ------- | --------- | ------ | ------ |
| **ChatBot** | v2.0.x | ✅ | 3.11.9 | Active Development |
| **Text2SQL** | v2.0.x | ✅ | 3.10.11 | Active Development |
| **Document Intelligence** | v1.5.x | ✅ | 3.10.11 | Active Development |
| **Speech2Text** | v1.4.x | ✅ | 3.10.11 | Active Development |
| **Stable Diffusion** | AUTOMATIC1111 v1.9.x | ✅ | 3.11.9 | Active Development |
| All Services | < v1.0 | ❌ | N/A | End of Life |

**Note:** We recommend always using the latest stable version for optimal security and features.

---

## 🚨 Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in AI-Assistant, please follow these guidelines:

### 🔐 Private Disclosure (Recommended)

**For critical vulnerabilities**, please report privately:

1. **Email:** [Your security email here]
2. **GitHub Security Advisory:** 
   - Go to https://github.com/SkastVnT/AI-Assistant/security/advisories
   - Click "Report a vulnerability"
   - Fill in the details securely

**Do NOT create public GitHub issues for security vulnerabilities.**

### 📝 What to Include

Please provide as much information as possible:

```
- Service affected (ChatBot/Text2SQL/Document Intelligence/Speech2Text/Stable Diffusion)
- Vulnerability type (e.g., SQL Injection, XSS, RCE, Prompt Injection)
- Steps to reproduce
- Proof of concept (code/screenshots)
- Impact assessment (CVSS score if possible)
- Suggested fix (if available)
- Your contact information for follow-up
```

### ⏱️ Response Timeline

| Stage | Timeline | Description |
| ----- | -------- | ----------- |
| **Acknowledgment** | Within 48 hours | We confirm receipt of your report |
| **Initial Assessment** | Within 5 business days | We evaluate severity and impact |
| **Status Update** | Every 7 days | Regular updates on investigation progress |
| **Fix Development** | 7-30 days | Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days) |
| **Public Disclosure** | 90 days max | After fix is released and deployed |

### 🏆 Recognition

- Valid security reports will be acknowledged in our [CHANGELOG](CHANGELOG.md)
- Critical findings may be eligible for a bug bounty (contact us for details)
- We maintain a [Hall of Fame](docs/SECURITY_HALL_OF_FAME.md) for security researchers

---

## 🛡️ Known Security Considerations

### 1️⃣ **API Keys & Secrets**

**Risk:** Exposure of sensitive credentials in code/logs

**Mitigations:**
- ✅ All API keys (Google Gemini, HuggingFace, OpenAI) stored in `.env` files
- ✅ `.env` files excluded via `.gitignore`
- ⚠️ **User Responsibility:** Never commit `.env` to version control
- ⚠️ **User Responsibility:** Rotate keys if accidentally exposed

**Check for leaks:**
```bash
# Scan git history for secrets
git log -p | grep -E "(api_key|API_KEY|SECRET|password)" --color=always

# Use truffleHog for deep scanning
pip install truffleHog
truffleHog --regex --entropy=True .
```

### 2️⃣ **SQL Injection (Text2SQL Service)**

**Risk:** User inputs converted to SQL queries without sanitization

**Mitigations:**
- ✅ Parameterized queries for PostgreSQL/MySQL/ClickHouse
- ✅ Input validation via LangChain's SQL agent
- ⚠️ **Limitation:** AI-generated SQL may bypass some filters
- 🔒 **Recommendation:** Use read-only database users for Text2SQL

**Secure Configuration:**
```python
# Text2SQL Services/src/database/connection.py
# Use restricted database user
DB_USER = "readonly_user"
DB_PERMISSIONS = "SELECT ONLY"
```

### 3️⃣ **Prompt Injection (ChatBot/Document Intelligence)**

**Risk:** Malicious prompts manipulating AI responses

**Mitigations:**
- ✅ System message filtering in ChatBot
- ✅ Content moderation via Google Gemini safety settings
- ⚠️ **Limitation:** Cannot completely prevent prompt injections
- 🔒 **Recommendation:** Validate AI outputs before executing actions

**Safety Configuration:**
```python
# ChatBot/src/agents/base_agent.py
safety_settings = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE"
}
```

### 4️⃣ **File Upload Vulnerabilities (Document Intelligence)**

**Risk:** Malicious file uploads (e.g., malware, XXE, path traversal)

**Mitigations:**
- ✅ File type validation (PDF, DOCX, images only)
- ✅ File size limits (50MB default)
- ✅ Uploads stored in isolated directory (`Document Intelligence Service/uploads/`)
- ⚠️ **Limitation:** No antivirus scanning (user responsibility)
- 🔒 **Recommendation:** Run service in sandboxed environment

**Validation Logic:**
```python
# Document Intelligence Service/src/utils/file_validator.py
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

### 5️⃣ **Dependency Vulnerabilities**

**Risk:** 159 known vulnerabilities detected by GitHub Dependabot (11 critical, 52 high)

**Status:** 🔴 **Requires Immediate Attention**

**Action Items:**
```bash
# Audit dependencies
pip install pip-audit
pip-audit -r requirements.txt

# Update vulnerable packages
pip install --upgrade torch transformers langchain

# Check specific CVEs
pip-audit --vulnerability-service osv
```

**High-Priority Updates:**
- `torch`: Update to 2.0.1+ (fixes CUDA memory vulnerabilities)
- `transformers`: Update to 4.30.0+ (fixes model injection attacks)
- `Pillow`: Update to 10.0.0+ (fixes image parsing RCE)
- `urllib3`: Update to 2.0.0+ (fixes CRLF injection)

### 6️⃣ **SSRF (Server-Side Request Forgery)**

**Risk:** Speech2Text service downloading models from HuggingFace Hub

**Mitigations:**
- ✅ Hardcoded model names (no user-supplied URLs)
- ✅ `use_auth_token` for authenticated downloads
- ⚠️ **Limitation:** HuggingFace Hub could be compromised
- 🔒 **Recommendation:** Verify model checksums after download

**Model Verification:**
```python
# Speech2Text Services/src/models/model_loader.py
import hashlib

def verify_model_checksum(model_path, expected_sha256):
    sha256 = hashlib.sha256()
    with open(model_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest() == expected_sha256
```

### 7️⃣ **CUDA/GPU Vulnerabilities**

**Risk:** GPU memory leaks, CUDA driver exploits

**Mitigations:**
- ✅ PyTorch 2.0.1 with patched CUDA 11.8
- ✅ Memory cleanup in inference loops
- ⚠️ **Limitation:** Driver-level vulnerabilities (NVIDIA responsibility)
- 🔒 **Recommendation:** Keep GPU drivers updated

**Check CUDA version:**
```bash
nvidia-smi
# Update drivers from: https://www.nvidia.com/drivers
```

### 8️⃣ **Prototype Pollution (JavaScript/Tailwind)**

**Risk:** Client-side vulnerabilities in ChatBot UI

**Mitigations:**
- ✅ No `eval()` or `Function()` constructors in frontend
- ✅ CSP (Content Security Policy) headers configured
- ✅ Tailwind CSS purged in production
- 🔒 **Recommendation:** Regularly update npm packages

**Check frontend dependencies:**
```bash
cd ChatBot
npm audit
npm audit fix --force
```

---

## 🔧 Security Best Practices for Deployment

### Production Checklist

- [ ] **Environment Variables:** All API keys in `.env`, never hardcoded
- [ ] **Firewall Rules:** Only expose necessary ports (5000-5004)
- [ ] **HTTPS/TLS:** Use reverse proxy (nginx) with SSL certificates
- [ ] **Database Security:** Use read-only users for Text2SQL, enable encryption at rest
- [ ] **Input Validation:** Sanitize all user inputs before processing
- [ ] **Rate Limiting:** Implement API rate limits (e.g., 100 req/min)
- [ ] **Logging:** Enable audit logs for sensitive operations (file uploads, SQL queries)
- [ ] **Container Security:** Run services in Docker with non-root users
- [ ] **Network Isolation:** Use Docker networks to isolate services
- [ ] **Backup Encryption:** Encrypt database backups with GPG

### Docker Security Configuration

```yaml
# docker-compose.yml (secure example)
services:
  chatbot:
    image: ai-assistant/chatbot:latest
    user: "1000:1000"  # Non-root user
    read_only: true    # Read-only filesystem
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}  # From .env
    networks:
      - ai_network
    
networks:
  ai_network:
    driver: bridge
    internal: true  # No external access
```

### Recommended Tools

| Tool | Purpose | Installation |
| ---- | ------- | ------------ |
| **Bandit** | Python security linter | `pip install bandit` |
| **Safety** | Dependency vulnerability scanner | `pip install safety` |
| **pip-audit** | PyPI package auditor | `pip install pip-audit` |
| **TruffleHog** | Secret scanner | `pip install truffleHog` |
| **Trivy** | Container vulnerability scanner | `docker pull aquasec/trivy` |
| **OWASP ZAP** | Web app security testing | https://www.zaproxy.org/ |

**Run security checks:**
```bash
# Python code security scan
bandit -r . -f json -o bandit-report.json

# Check for known vulnerabilities
safety check --json

# Audit installed packages
pip-audit --desc

# Scan Docker images
trivy image ai-assistant/chatbot:latest
```

---

## 📚 Security Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP AI Security Guide](https://owasp.org/www-project-ai-security-and-privacy-guide/)
- [LangChain Security Best Practices](https://python.langchain.com/docs/security)
- [HuggingFace Model Security](https://huggingface.co/docs/hub/security)

### Relevant CVEs
- **CVE-2023-XXXXX:** PyTorch CUDA RCE (Fixed in 2.0.1)
- **CVE-2023-YYYYY:** Transformers Model Injection (Fixed in 4.30.0)
- **CVE-2023-ZZZZZ:** Pillow Image Parsing RCE (Fixed in 10.0.0)

### Training
- [Secure Python Coding](https://www.udemy.com/course/secure-python/)
- [AI Security Fundamentals](https://www.coursera.org/learn/ai-security)

---

## 🤝 Security Team

For security-related questions, contact:

- **Lead Maintainer:** [@SkastVnT](https://github.com/SkastVnT)
- **Security Email:** [Your security email]
- **GitHub Security:** https://github.com/SkastVnT/AI-Assistant/security

---

## 📝 Changelog

| Date | Severity | Description | Status |
| ---- | -------- | ----------- | ------ |
| 2025-11-06 | Info | Initial SECURITY.md created | ✅ Done |
| TBD | High | Audit and fix 159 Dependabot vulnerabilities | 🔴 Pending |
| TBD | Medium | Implement rate limiting on all API endpoints | 🔴 Pending |
| TBD | Medium | Add antivirus scanning for file uploads | 🔴 Pending |

---

## ⚖️ Responsible Disclosure

We follow **responsible disclosure** principles:

1. **Report privately** to security team
2. **Give us 90 days** to fix before public disclosure
3. **Coordinate disclosure** timing with us
4. **No exploitation** of vulnerabilities for malicious purposes
5. **No data exfiltration** from live systems

**Thank you for helping keep AI-Assistant secure! 🙏**

---

*Last Updated: November 6, 2025*
*Version: 1.0*
