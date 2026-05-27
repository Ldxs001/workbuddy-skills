#!/usr/bin/env python3
"""Find non-raw string literals containing \Z in all .py files under a directory."""
import tokenize, io, os, sys

base = 'C:/Users/sm001/.workbuddy/skills/skill-standardization/scripts'
results = []
for root, dirs, files in os.walk(base):
    for f in sorted(files):
        if not f.endswith('.py'):
            continue
        fp = os.path.join(root, f)
        try:
            with open(fp, 'rb') as ff:
                toks = list(tokenize.generate_tokens(io.BytesIO(ff.read()).readline))
        except Exception as e:
            continue
        for t in toks:
            if t.type == tokenize.STRING:
                s = t.string
                # Check if it's a raw string (prefix contains r or R)
                prefix = ''
                if s[0] in ('"', "'"):
                    pass  # no prefix
                elif s[1] in ('"', "'"):
                    prefix = s[0]
                if 'r' in prefix.lower():
                    continue  # raw string, \Z is fine
                # Check for literal \Z in the string value
                # The token includes quotes, so we need to check the actual content
                # A non-raw string with \Z would have \\Z in the source (escaped backslash + Z)
                # But we're looking at the tokenized string, so \Z in the VALUE means source had \\Z
                # Actually - the tokenize module gives us the STRING AS WRITTEN IN SOURCE
                # So a non-raw string '...\Z...' in source would be token '...\Z...'
                # And Python would have already warned about it during compilation
                # Let's just check if '\Z' appears in the token string (after the prefix)
                raw_tok = s
                if raw_tok[0] not in ('"', "'"):
                    # has prefix
                    raw_tok = raw_tok[1:]
                if '\\Z' in raw_tok or r'\Z' in raw_tok:
                    # Check if it's truly a problem (not \\Z which is escaped backslash + Z)
                    # In a non-raw string, \Z is a single backslash + Z
                    # The token will show '\\Z' (escaped in representation) if source had \Z
                    pass  # handled below with byte search instead
        # Fallback: byte-level search for b'\\Z' in source (non-raw \Z)
        try:
            src = open(fp, 'rb').read()
            pos = 0
            while True:
                pos = src.find(b'\\Z', pos)
                if pos == -1:
                    break
                # Check if this \Z is inside a raw string context (heuristic)
                # Look backwards for the string start
                context = src[max(0,pos-50):pos+5]
                context_str = context.decode('utf-8', errors='replace')
                # If we see r' or r" before \Z (within reason), it's raw - skip
                if 'r"' in context_str or "r'" in context_str:
                    # Could be raw, skip (heuristic)
                    pass
                else:
                    rel = fp.replace('C:/Users/sm001/.workbuddy/skills/skill-standardization/', '')
                    results.append((rel, pos))
                pos += 1
        except Exception as e:
            pass

print(f"Found {len(results)} files with potential non-raw \\Z:")
for rel, pos in results:
    print(f"  {rel}: byte {pos}")
if not results:
    print("  (none found)")
