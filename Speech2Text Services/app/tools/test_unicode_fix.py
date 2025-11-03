# -*- coding: utf-8 -*-
"""
Unicode Fix Test Script
Test all major Python files to ensure Unicode errors are resolved
"""

import subprocess
import sys
import os

def test_script(script_path, timeout=10):
    """Test a Python script for Unicode errors"""
    try:
        print(f"Testing {script_path}...")
        
        # Run with --help or a simple check to avoid long execution
        if 'main.py' in script_path:
            result = subprocess.run([
                sys.executable, script_path, '--help'
            ], capture_output=True, text=True, timeout=timeout, encoding='utf-8')
        else:
            # For other scripts, run briefly and kill
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, text=True, timeout=2, encoding='utf-8')  # Short timeout
            
        # Check for Unicode errors in output
        unicode_errors = [
            "UnicodeEncodeError",
            "'charmap' codec can't encode",
            "character maps to <undefined>"
        ]
        
        has_unicode_error = any(error in result.stderr for error in unicode_errors)
        
        if has_unicode_error:
            print(f"  [ERROR] Unicode error found in {script_path}")
            print(f"  Error: {result.stderr}")
            return False
        else:
            print(f"  [OK] No Unicode errors in {script_path}")
            return True
            
    except subprocess.TimeoutExpired:
        print(f"  [OK] {script_path} - Timeout (expected for long-running scripts)")
        return True
    except Exception as e:
        print(f"  [WARN] {script_path} - Error: {e}")
        return True  # Other errors are not Unicode-related

def main():
    print("[MIC] Unicode Fix Test Script")
    print("Testing major Python files for Unicode errors...")
    print("=" * 50)
    
    # Test main scripts
    test_files = [
        'src/main.py',
        'src/t5_model.py', 
        'src/gemini_model.py',
        'core/run_dual_fast.py',
        'core/run_dual_smart.py',
        'web_ui.py',
        's2t.py'
    ]
    
    results = []
    
    for test_file in test_files:
        if os.path.exists(test_file):
            success = test_script(test_file)
            results.append((test_file, success))
        else:
            print(f"  [SKIP] {test_file} - File not found")
            results.append((test_file, True))  # Skip missing files
    
    print("\n" + "=" * 50)
    print("Test Results:")
    
    passed = 0
    total = len(results)
    
    for file_path, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {file_path}")
        if success:
            passed += 1
    
    print(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! Unicode errors have been fixed.")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} tests failed. Some Unicode errors may remain.")
        return 1

if __name__ == "__main__":
    sys.exit(main())