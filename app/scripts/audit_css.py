#!/usr/bin/env python3
"""CSS/HTML class audit script."""

import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_PATH = os.path.join(BASE, "services", "chatbot", "templates", "index.html")
CSS_DIR = os.path.join(BASE, "services", "chatbot", "static", "css")

with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()
html_lines = html.splitlines()

# --- collect all class names from HTML ---
class_names = set()
for m in re.finditer(r'class="([^"]+)"', html):
    for cls in m.group(1).split():
        class_names.add(cls)

# --- load all CSS ---
all_css = ""
css_by_file = {}
for fname in sorted(os.listdir(CSS_DIR)):
    if fname.endswith(".css"):
        with open(os.path.join(CSS_DIR, fname), encoding="utf-8") as fp:
            content = fp.read()
            css_by_file[fname] = content
            all_css += content + "\n"

# --- find all selectors defined in CSS (rough: .classname{ ) ---
css_selectors = set()
for m in re.finditer(r"\.([\w_-]+)", all_css):
    css_selectors.add(m.group(1))

# --- find classes in HTML with no rule at all in CSS ---
no_css = []
for cls in sorted(class_names):
    if cls not in css_selectors:
        no_css.append(cls)

# --- find duplicate selectors in app.css ---
appcss = css_by_file.get("app.css", "")
all_selectors_in_appcss = re.findall(r"^(\.[^\s{,]+)\s*\{", appcss, re.MULTILINE)
from collections import Counter

counts = Counter(all_selectors_in_appcss)
dups = [(s, c) for s, c in counts.items() if c > 1]

# --- find CSS selectors NOT used anywhere in HTML (static check only) ---
# build set of selectors defined in CSS
defined_selectors = set()
for m in re.finditer(r"^\.([\w_-]+)", all_css, re.MULTILINE):
    defined_selectors.add(m.group(1))

# HTML uses: class_names set
orphaned = sorted(defined_selectors - class_names)

# --- output ---
print("=" * 70)
print("CSS / HTML AUDIT REPORT")
print("=" * 70)

print("\n[STATS]")
print(f"  HTML classes found:          {len(class_names)}")
print(f"  CSS class selectors defined: {len(css_selectors)}")
print(f"  Matched (HTML in CSS):       {len(class_names & css_selectors)}")
print(f"  HTML classes missing in CSS: {len(no_css)}")
print(f"  CSS selectors not in HTML:   {len(orphaned)}")
print(f"  Duplicate selectors (app.css):{len(dups)}")

print(f"\n[UNDECLARED] Classes in HTML but no CSS rule ({len(no_css)})")
for c in no_css:
    # find first occurrence in HTML
    for i, line in enumerate(html_lines, 1):
        if f" {c}" in line or f'"{c}' in line or f' {c}"' in line:
            print(f"  .{c}  (first at line {i})")
            break
    else:
        print(f"  .{c}")

print(f"\n[DUPLICATES] Selectors defined multiple times in app.css ({len(dups)})")
for sel, count in sorted(dups, key=lambda x: x[0]):
    lines_found = [
        i + 1
        for i, line_text in enumerate(appcss.splitlines())
        if re.match(r"\s*" + re.escape(sel) + r"\s*\{", line_text)
    ]
    print(f"  {sel}: {count}x at lines {lines_found}")

print(
    f"\n[ORPHANED IN CSS] CSS selectors not found in static HTML (top 50 of {len(orphaned)})"
)
print("  (Many are dynamically injected by JS — see notes)")
for c in orphaned[:50]:
    print(f"  .{c}")
if len(orphaned) > 50:
    print(f"  ... and {len(orphaned) - 50} more")
