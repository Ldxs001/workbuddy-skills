#!/usr/bin/env python3
"""Search for literal backslash+Z in Python source files.
A normal string '\Z' triggers SyntaxWarning in Python 3.12+.
Raw strings r'\Z' are fine.
"""
import os

scripts_dir = "C:/Users/sm001/.workbuddy/skills/skill-standardization/scripts"
results = []

for root, dirs, files in os.walk(scripts_dir):
    for fname in sorted(files):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "rb") as f:
            data = f.read()
        # Search for literal backslash + Z in the binary data
        pos = 0
        while True:
            pos = data.find(b'\\Z', pos)
            if pos == -1:
                break
            # Get context around the match
            start = max(0, pos - 40)
            end = min(len(data), pos + 5)
            context = data[start:end]
            try:
                context_str = context.decode("utf-8", errors="replace")
            except:
                context_str = str(context)
            results.append((fpath, pos, context_str))
            pos += 1

print(f"Found {len(results)} occurrences of literal \\Z in source files:")
for fpath, pos, context in results:
    rel = fpath.replace("C:/Users/sm001/.workbuddy/skills/skill-standardization/", "")
    print(f"  {rel} @ pos {pos}: ...{context}...")

if not results:
    print("  (none found via binary search)")
    print("  The SyntaxWarning may be from a dynamically-constructed regex string.")
