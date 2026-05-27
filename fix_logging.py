#!/usr/bin/env python3
"""Fix clear-text logging of sensitive message content in chatbot_main.py"""
import re

path = "services/chatbot/chatbot_main.py"
content = open(path, encoding="utf-8-sig").read()

replacements = [
    (
        '[TOOLS] Auto web search triggered for: {message[:60]}',
        '[TOOLS] Auto web search triggered',
    ),
    (
        '[TOOLS] PDF Analyzer for: {message[:80]}',
        '[TOOLS] PDF Analyzer triggered',
    ),
    (
        '[TOOLS] Translation for: {message[:80]}',
        '[TOOLS] Translation triggered',
    ),
    (
        '[TOOLS] Memory Manager for: {message[:80]}',
        '[TOOLS] Memory Manager triggered',
    ),
]

for old_fragment, new_fragment in replacements:
    old = f'logger.info(f"[TOOLS] {old_fragment[7:]}")'
    new = f'logger.info("{new_fragment}")'
    # Build actual strings
    old_str = 'logger.info(f"' + old_fragment + '")'
    new_str = 'logger.info("' + new_fragment + '")'
    if old_str in content:
        content = content.replace(old_str, new_str)
        print(f"Replaced: {old_fragment}")
    else:
        print(f"NOT FOUND: {old_fragment}")

# Handle Deep Research which may have a non-ASCII emoji
# Find by context and replace the line
lines = content.split('\n')
new_lines = []
for line in lines:
    if 'Deep Research triggered for:' in line and 'logger.info' in line:
        # Replace the whole log line
        indent = len(line) - len(line.lstrip())
        new_lines.append(' ' * indent + 'logger.info("[TOOLS] Deep Research triggered")')
        print(f"Replaced Deep Research log line")
    else:
        new_lines.append(line)
content = '\n'.join(new_lines)

open(path, 'w', encoding='utf-8-sig').write(content)
print("Saved.")
