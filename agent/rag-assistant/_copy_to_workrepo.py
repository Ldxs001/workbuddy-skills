import shutil, os, re

src = r'C:\Users\sm001\WorkBuddy\rag-assistant'
dst = r'C:\Users\sm001\.workbuddy\workbuddy-skills\agent\rag-assistant'

def ignore_f(dir, files):
    ignores = {'__pycache__'}
    for f in files:
        fp = os.path.join(dir, f)
        if os.path.isdir(fp):
            rel = os.path.relpath(fp, src).replace(os.sep, '/')
            if rel.startswith('data/models') or rel.startswith('data/kb') or rel.startswith('data/cache') or rel.startswith('vendor'):
                ignores.add(f)
    return ignores

os.makedirs(dst, exist_ok=True)
shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore_f)

v = open(os.path.join(dst, 'rag_assistant', '__init__.py')).read()
m = re.search(r'__version__ = "([^"]+)"', v)
print('Copied. Version:', m.group(1) if m else 'unknown')
