#!/usr/bin/env python3
"""
Bandit report parser that fails the CI only on HIGH severity findings.
Usage: python bandit_fail_on_high.py <bandit-report.json>
"""
import json
import sys

if len(sys.argv) != 2:
    print('Usage: bandit_fail_on_high.py <bandit-report.json>')
    sys.exit(1)

report_path = sys.argv[1]

try:
    with open(report_path, 'r') as f:
        report = json.load(f)
except FileNotFoundError:
    print(f'Error: Report file {report_path} not found')
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f'Error: Failed to parse JSON report: {e}')
    sys.exit(1)

results = report.get('results', [])
high_findings = [r for r in results if r.get('issue_severity') == 'HIGH']

print(f'Total findings: {len(results)}')
print(f'HIGH severity findings: {len(high_findings)}')

if high_findings:
    print('\n⚠️  HIGH severity security issues found:')
    for finding in high_findings:
        print(f"\n  File: {finding.get('filename', 'N/A')}")
        print(f"  Line: {finding.get('line_number', 'N/A')}")
        print(f"  Issue: {finding.get('issue_text', 'N/A')}")
        print(f"  Test ID: {finding.get('test_id', 'N/A')}")
        print(f"  Confidence: {finding.get('issue_confidence', 'N/A')}")
    print('\n❌ Failing build due to HIGH severity findings.')
    sys.exit(1)
else:
    print('✅ No HIGH severity findings. Build passing.')
    sys.exit(0)
