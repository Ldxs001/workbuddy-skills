#!/usr/bin/env python3
"""Find non-raw string literals containing \Z in .py files.
Uses tokenize (operates on source without compiling)."""
import os, tokenize, io

scripts_dir = "C:/Users/sm001/.workbuddy/skills/skill-standardization/scripts"
results = []

for root, dirs, files in os.walk(scripts_dir):
    for fname in sorted(files):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, "rb") as f:
                tokens = list(tokenize.generate_tokens(io.BytesIO(f.read()).readline))
        except Exception:
            continue
        for i, tok in enumerate(tokens):
            if tok.type == tokenize.STRING:
                # Check if it's a raw string: prefix contains 'r' or 'R'
                raw = False
                # The string token includes the quote chars; prefix is before the quote
                # Actually, tokenize returns the full string including prefix
                s = tok.string
                # Check if prefix contains r/R
                # String tokens: r'...'  f'...'  rf'...' etc.
                # The prefix is the part before the quote char
                # We need to check if 'r' or 'R' is in the prefix
                # Find where the string content starts (after prefix and opening quote)
                # Simpler: check if first char of token is r/R
                if s and s[0] in ('r', 'R'):
                    raw = True
                # Also check for rb'...' or br'...'
                if len(s) >= 2 and s[0].lower() == 'b' and s[1].lower() == 'r':
                    raw = True
                if len(s) >= 2 and s[0].lower() == 'r' and s[1].lower() == 'b':
                    raw = True
                # Decode the string to check content
                # For simplicity, just check if '\Z' is in the token string
                # (this is a heuristic - the actual \Z in source would be \\Z in the token)
                if raw:
                    continue
                # Check the actual source text for \Z not preceded by r/R on the same line
                # Simpler approach: just search file content for '\Z' not in raw strings
                pass  # handled below with line-based approach

    # Line-based approach (simpler and more reliable)
results2 = []
for root, dirs, files in os.walk(scripts_dir):
    for fname in sorted(files):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        in_multiline_single = False
        in_multiline_double = False
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip("\n")
            # Track triple-quote state (rough)
            if '"""' in stripped:
                in_multiline_double = not in_multiline_double
            if "'''" in stripped and not in_multiline_double:
                in_multiline_single = not in_multiline_single
            if in_multiline_single or in_multiline_double:
                continue
            # Check for '\Z' or "\Z" in non-raw strings
            # Simple check: line contains \Z and doesn't contain r'\Z' or r"\Z"
            if r'\Z' in stripped or '\\Z' in stripped:
                # Skip if it's in a comment
                comment_pos = stripped.find("#")
                # Check if \Z appears before the comment
                z_pos = stripped.find('\\Z')
                if z_pos == -1:
                    z_pos = stripped.find("'\\Z'")
                if z_pos != -1 and (comment_pos == -1 or z_pos < comment_pos):
                    results2.append((fpath, i, stripped.strip()))

# Deduplicate and print
seen = set()
print(f"Found {len(results2)} lines with \\Z:")
for fpath, ln, content in results2:
    key = (fpath, ln)
    if key in seen:
        continue
    seen.add(key)
    rel = fpath.replace("C:/Users/sm001/.workbuddy/skills/skill-standardization/", "")
    print(f"  {rel}:{ln}: {content[:140]}")
if not results2:
    print("  (none found)")
