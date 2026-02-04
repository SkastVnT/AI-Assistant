# Security Audit Report

**Generated:** 2026-02-02 10:39:22 UTC  
**Tool:** Bandit v1.9.3  
**Scan Scope:** All Python code (excluding tests, venv, ComfyUI)

## Executive Summary

- **Total Issues Found:** 120
- **HIGH Severity:** 16
- **MEDIUM Severity:** 104
- **LOW Severity:** 0

## Severity Breakdown

### Critical Findings (Require Immediate Action)


#### subprocess_popen_with_shell_equals_true (B602)

**Issue:** subprocess call with shell=True identified, security issue.  
**Occurrences:** 3  
**Confidence:** HIGH  

**Affected Files:**
1. `./scripts/deploy_public.py:131`
2. `./scripts/utilities/service_health_checker.py:237`
3. `./scripts/utilities/service_health_checker.py:335`


#### hashlib (B324)

**Issue:** Use of weak MD5 hash for security. Consider usedforsecurity=False  
**Occurrences:** 8  
**Confidence:** HIGH  

**Affected Files:**
1. `./services/chatbot/app/controllers/chat_controller.py:206`
2. `./services/chatbot/app/services/cache_service.py:98`
3. `./services/chatbot/database/utils/cache_optimizer.py:219`
4. `./services/hub-gateway/utils/cache.py:33`
5. `./services/lora-training/utils/dataset_tools.py:376`
6. `./services/lora-training/utils/redis_manager.py:238`
7. `./services/speech2text/app/core/utils/cache.py:31`
8. `./src/utils/cache.py:33`


#### flask_debug_true (B201)

**Issue:** A Flask app appears to be run with debug=True, which exposes the Werkzeug debugger and allows the execution of arbitrary code.  
**Occurrences:** 5  
**Confidence:** MEDIUM  

**Affected Files:**
1. `./services/speech2text/app/tools/web_ui.py:283`
2. `./services/speech2text/scripts/test_webui_simple.py:152`
3. `./services/text2sql/app_simple.py:980`
4. `./services/text2sql/scripts/no_gemini.py:1504`
5. `./services/text2sql/scripts/test.py:1118`


### Medium Priority Issues


#### huggingface_unsafe_download (B615)

**Issue:** Unsafe Hugging Face Hub download without revision pinning in from_pretrained()  
**Occurrences:** 65  
**Confidence:** HIGH  
**Example:** `./services/chatbot/src/utils/local_model_loader.py:61`


#### hardcoded_bind_all_interfaces (B104)

**Issue:** Possible binding to all interfaces.  
**Occurrences:** 24  
**Confidence:** MEDIUM  
**Example:** `./config/model_config.py:39`


#### pytorch_load (B614)

**Issue:** Use of unsafe PyTorch load  
**Occurrences:** 7  
**Confidence:** HIGH  
**Example:** `./services/image-upscale/src/upscale_tool/multi_upscaler.py:108`


#### exec_used (B102)

**Issue:** Use of exec detected.  
**Occurrences:** 3  
**Confidence:** HIGH  
**Example:** `./scripts/fix_dependencies.py:121`


#### blacklist (B307)

**Issue:** Use of possibly insecure function - consider using safer ast.literal_eval.  
**Occurrences:** 3  
**Confidence:** HIGH  
**Example:** `./services/mcp-server/server.py:295`


#### blacklist (B301)

**Issue:** Pickle and modules that wrap it can be unsafe when used to deserialize untrusted data, possible security issue.  
**Occurrences:** 1  
**Confidence:** HIGH  
**Example:** `./services/hub-gateway/utils/google_drive_uploader.py:52`


#### hardcoded_sql_expressions (B608)

**Issue:** Possible SQL injection vector through string-based query construction.  
**Occurrences:** 1  
**Confidence:** MEDIUM  
**Example:** `./services/mcp-server/tools/advanced_tools.py:238`


## Recommendations

### Immediate Actions (HIGH Priority)

1. **Disable Flask Debug Mode in Production**
   - Review all Flask app configurations
   - Ensure `debug=False` in production environments
   - Use environment variables for configuration

2. **Replace MD5 with Secure Hash Functions**
   - Migrate to SHA-256 for security-sensitive operations
   - Use `usedforsecurity=False` for non-security uses of MD5

3. **Fix Shell Injection Vulnerabilities**
   - Remove `shell=True` from subprocess calls
   - Use list-based command arguments
   - Implement strict input validation

### Short-term Actions (MEDIUM Priority)

1. **Pin Hugging Face Model Revisions**
   - Specify exact model versions in production
   - Implement model verification

2. **Secure PyTorch Model Loading**
   - Use `weights_only=True` for untrusted sources
   - Validate checkpoint files before loading

3. **Review exec() and eval() Usage**
   - Replace with safer alternatives where possible
   - Implement strict sandboxing for code execution features

4. **Implement Pickle Security**
   - Avoid unpickling untrusted data
   - Use safer serialization formats (JSON)

### Long-term Actions

1. **Regular Security Audits**
   - Schedule quarterly security reviews
   - Implement automated security scanning in CI/CD

2. **Security Training**
   - Provide security training for contributors
   - Establish secure coding guidelines

3. **Penetration Testing**
   - Conduct professional security assessment
   - Test all service endpoints

4. **Bug Bounty Program**
   - Consider establishing a bug bounty program
   - Encourage responsible disclosure

## Testing

All security issues should be verified and tested after fixes are applied:

```bash
# Re-run security scan
python -m bandit -r . --exclude ./venv*,./ComfyUI,**/tests/** -f json -o bandit-report-after.json

# Compare results
diff bandit-report-before.json bandit-report-after.json

# Run security tests
pytest tests/unit/test_security.py -v
```

## Next Review

**Scheduled:** 90 days from report date  
**Trigger for earlier review:**
- Major code changes
- New service additions
- Security incident
- Vulnerability disclosure

---

For detailed findings, see the complete JSON report: `bandit-report.json`
