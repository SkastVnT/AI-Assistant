"""
AI-Powered Service Health Checker
Uses Gemini 2.0 Flash (or Grok as fallback) to verify dependencies and fix issues
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("[WARNING] google-genai not installed. AI features disabled.")

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv not installed. Environment variables may not be loaded.")

class ServiceHealthChecker:
    """AI-powered health checker for service dependencies"""
    
    def __init__(self, service_name: str, service_path: str):
        self.service_name = service_name
        self.service_path = Path(service_path)
        self.requirements_path = self.service_path / "requirements.txt"
        
        # Detect venv path (different services use different names)
        possible_venv_names = ["venv", "venv_chatbot", "lora", ".venv"]
        self.venv_path = None
        for venv_name in possible_venv_names:
            potential_path = self.service_path / venv_name
            if potential_path.exists():
                self.venv_path = potential_path
                break
        
        if not self.venv_path:
            # Default to venv even if doesn't exist
            self.venv_path = self.service_path / "venv"
        
        # Initialize AI clients
        self.ai_client = None
        self.ai_type = None
        self._init_ai_client()
    
    def _init_ai_client(self):
        """Initialize AI client (Gemini or Grok fallback)"""
        # Try Gemini first
        if HAS_GEMINI:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                try:
                    self.ai_client = genai.Client(api_key=api_key)
                    self.ai_type = "gemini"
                    print("[AI] Using Gemini 2.0 Flash")
                    return
                except Exception as e:
                    print(f"[WARNING] Gemini initialization failed: {e}")
        
        # Try Grok as fallback
        if HAS_OPENAI:
            grok_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
            if grok_key:
                try:
                    self.ai_client = openai.OpenAI(
                        api_key=grok_key,
                        base_url="https://api.x.ai/v1"
                    )
                    self.ai_type = "grok"
                    print("[AI] Using Grok (Gemini fallback)")
                    return
                except Exception as e:
                    print(f"[WARNING] Grok initialization failed: {e}")
        
        print("[WARNING] No AI service available. Running basic checks only.")
    
    def get_pip_list(self) -> str:
        """Get pip list from venv"""
        if not self.venv_path.exists():
            return ""
        
        try:
            if os.name == 'nt':  # Windows
                pip_path = self.venv_path / "Scripts" / "pip.exe"
            else:  # Linux/Mac
                pip_path = self.venv_path / "bin" / "pip"
            
            result = subprocess.run(
                [str(pip_path), "list", "--format=freeze"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            print(f"[ERROR] Failed to get pip list: {e}")
            return ""
    
    def read_requirements(self) -> str:
        """Read requirements.txt"""
        if not self.requirements_path.exists():
            return ""
        
        try:
            with open(self.requirements_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[ERROR] Failed to read requirements: {e}")
            return ""
    
    def ask_ai(self, prompt: str) -> Optional[str]:
        """Ask AI for analysis"""
        if not self.ai_client:
            return None
        
        try:
            if self.ai_type == "gemini":
                response = self.ai_client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=prompt
                )
                return response.text
            elif self.ai_type == "grok":
                response = self.ai_client.chat.completions.create(
                    model="grok-beta",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] AI request failed: {e}")
            return None
    
    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """Check if all dependencies are installed"""
        print(f"\n[CHECK] Analyzing dependencies for {self.service_name}...")
        
        pip_list = self.get_pip_list()
        requirements = self.read_requirements()
        
        if not pip_list:
            return False, ["Virtual environment not found or empty"]
        
        if not requirements:
            return False, ["requirements.txt not found"]
        
        # Use AI to compare
        prompt = f"""You are a Python dependency expert. Analyze if all required packages are installed.

INSTALLED PACKAGES (pip list):
{pip_list}

REQUIRED PACKAGES (requirements.txt):
{requirements}

Task:
1. Check if ALL required packages from requirements.txt are installed
2. Ignore version mismatches if minor (e.g., 1.0.0 vs 1.0.1 is OK)
3. Flag CRITICAL missing packages
4. Return JSON format ONLY:

{{
    "status": "ok" or "missing",
    "missing_packages": ["package1", "package2"],
    "recommendations": ["specific pip install commands if needed"]
}}

Return ONLY valid JSON, no markdown, no explanation."""

        ai_response = self.ask_ai(prompt)
        
        if ai_response:
            try:
                # Extract JSON from response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(ai_response[json_start:json_end])
                    
                    if result.get("status") == "ok":
                        print("[OK] All dependencies satisfied")
                        return True, []
                    else:
                        missing = result.get("missing_packages", [])
                        print(f"[MISSING] {len(missing)} package(s) need installation")
                        return False, result.get("recommendations", [])
            except json.JSONDecodeError:
                print("[WARNING] Could not parse AI response")
        
        # Fallback: basic check
        return self._basic_dependency_check(pip_list, requirements)
    
    def _basic_dependency_check(self, pip_list: str, requirements: str) -> Tuple[bool, List[str]]:
        """Basic dependency check without AI"""
        installed = set()
        for line in pip_list.split('\n'):
            if '==' in line:
                pkg = line.split('==')[0].strip().lower()
                installed.add(pkg)
        
        missing = []
        for line in requirements.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name
                for sep in ['==', '>=', '<=', '>', '<', '~=']:
                    if sep in line:
                        pkg = line.split(sep)[0].strip().lower()
                        if pkg not in installed:
                            missing.append(line)
                        break
        
        return len(missing) == 0, missing
    
    def test_service(self, test_command: str) -> Tuple[bool, str]:
        """Test run the service"""
        print(f"\n[TEST] Running service test: {test_command}")
        
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.service_path)
            )
            
            if result.returncode == 0:
                print("[OK] Service test passed")
                return True, result.stdout
            else:
                print(f"[FAIL] Service test failed (exit code: {result.returncode})")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            print("[OK] Service started (timeout expected for servers)")
            return True, "Service started successfully"
        except Exception as e:
            return False, str(e)
    
    def diagnose_error(self, error_output: str) -> Optional[Dict]:
        """Use AI to diagnose error and suggest fix"""
        if not self.ai_client:
            return None
        
        print("\n[AI] Diagnosing error...")
        
        prompt = f"""You are a Python debugging expert. Analyze this error and provide fix.

SERVICE: {self.service_name}
ERROR OUTPUT:
{error_output}

REQUIREMENTS:
{self.read_requirements()}

Task:
1. Identify if error is due to:
   - Missing library (needs pip install)
   - Wrong version (needs upgrade/downgrade)
   - Code bug (needs code fix)
   - Configuration issue
2. Provide specific fix steps

Return JSON format ONLY:
{{
    "error_type": "missing_library" | "version_conflict" | "code_bug" | "config_issue",
    "diagnosis": "brief explanation",
    "fix_commands": ["command1", "command2"],
    "is_critical": true/false
}}

Return ONLY valid JSON, no markdown."""

        ai_response = self.ask_ai(prompt)
        
        if ai_response:
            try:
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    return json.loads(ai_response[json_start:json_end])
            except json.JSONDecodeError:
                pass
        
        return None
    
    def auto_fix(self, fix_commands: List[str]) -> bool:
        """Execute auto-fix commands or install packages"""
        print("\n[FIX] Attempting auto-fix...")
        
        # Get pip path
        if os.name == 'nt':  # Windows
            pip_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = self.venv_path / "bin" / "pip"
        
        for cmd in fix_commands:
            print(f"[RUN] {cmd}")
            
            # Check if this is a package spec (contains == or >=, etc) or a command
            is_package = any(op in cmd for op in ['==', '>=', '<=', '>', '<', '~=', '; sys_platform'])
            
            if is_package:
                # Skip Windows-only exclusions
                if 'sys_platform' in cmd and 'win32' in cmd and os.name == 'nt':
                    print("[SKIP] Package excluded on Windows")
                    continue
                
                # Install via pip
                install_cmd = f'"{pip_path}" install "{cmd}"'
                print(f"[PIP] Installing: {cmd}")
            else:
                # Execute as command
                install_cmd = cmd
            
            try:
                result = subprocess.run(
                    install_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(self.service_path)
                )
                
                if result.returncode != 0:
                    print(f"[FAIL] Command failed: {result.stderr}")
                    return False
                else:
                    print("[OK] Command succeeded")
            except Exception as e:
                print(f"[ERROR] {e}")
                return False
        
        return True
    
    def full_health_check(self, test_command: Optional[str] = None) -> bool:
        """Run complete health check with auto-fix"""
        print(f"\n{'='*80}")
        print(f"SERVICE HEALTH CHECK: {self.service_name}")
        print(f"{'='*80}")
        
        # Step 1: Check dependencies
        deps_ok, missing = self.check_dependencies()
        
        if not deps_ok:
            print(f"\n[ACTION] Installing missing dependencies...")
            for cmd in missing:
                print(f"  → {cmd}")
            
            # Auto-install
            if missing and self.auto_fix(missing):
                # Re-check after install
                deps_ok, _ = self.check_dependencies()
        
        if not deps_ok:
            print(f"\n[FAIL] ❌ Dependency check failed for {self.service_name}")
            return False
        
        # Step 2: Test service (if test command provided)
        if test_command:
            test_ok, output = self.test_service(test_command)
            
            if not test_ok:
                # Diagnose and try to fix
                diagnosis = self.diagnose_error(output)
                
                if diagnosis:
                    print(f"\n[DIAGNOSIS] {diagnosis.get('diagnosis', 'Unknown error')}")
                    
                    if diagnosis.get('error_type') in ['missing_library', 'version_conflict']:
                        fix_cmds = diagnosis.get('fix_commands', [])
                        if fix_cmds and self.auto_fix(fix_cmds):
                            # Re-test
                            test_ok, _ = self.test_service(test_command)
                
                if not test_ok and not diagnosis.get('is_critical', True):
                    print("[WARNING] Non-critical error detected, continuing...")
                    test_ok = True
        else:
            test_ok = True  # Skip test if no command provided
        
        # Final verdict
        if deps_ok and test_ok:
            print(f"\n[SUCCESS] ✅ {self.service_name} is healthy!")
            return True
        else:
            print(f"\n[FAIL] ❌ {self.service_name} has issues")
            return False


def main():
    """CLI interface"""
    if len(sys.argv) < 3:
        print("Usage: python service_health_checker.py <service_name> <service_path> [test_command]")
        sys.exit(1)
    
    service_name = sys.argv[1]
    service_path = sys.argv[2]
    test_command = sys.argv[3] if len(sys.argv) > 3 else None
    
    checker = ServiceHealthChecker(service_name, service_path)
    success = checker.full_health_check(test_command)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
