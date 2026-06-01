r"""extract_simple.py - 极简版提取，不卡死。
用法: python extract_simple.py <input.tex> <output_dir>
"""
import json, os, sys

def main():
    tex_path = sys.argv[1]
    output_dir = sys.argv[2]
    with open(tex_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 找 \begin{document} 和 \end{document}
    bs = text.find(r"\begin{document}")
    be = text.find(r"\end{document}")
    preamble = text[:bs].strip() if bs != -1 else ""
    body = text[bs+len(r"\begin{document}"):be].strip() if be != -1 else ""

    # 保存 body
    body_dir = os.path.join(output_dir, "scripts", "components", "body")
    os.makedirs(body_dir, exist_ok=True)
    with open(os.path.join(body_dir, "body.tex"), "w", encoding="utf-8") as f:
        f.write(body + "\n")

    # 把 preamble 按行分割
    plines = preamble.splitlines()
    components = []

    # 1. documentclass
    for ln in plines:
        s = ln.strip()
        if s.startswith(r"\documentclass"):
            d = os.path.join(output_dir, "scripts", "components", "preamble")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "class-settings.tex"), "w", encoding="utf-8") as f:
                f.write(s.rstrip() + "\n")
            components.append({"type":"preamble","name":"class-settings","path":"preamble/class-settings.tex","category":"class","description":"文档类"})
            break

    # 2. usepackage 行（直接按行收集，不分组）
    pkg_lines = [l.strip() for l in plines if l.strip().startswith(r"\usepackage")]
    if pkg_lines:
        d = os.path.join(output_dir, "scripts", "components", "preamble")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "packages.tex"), "w", encoding="utf-8") as f:
            f.write("\n".join(pkg_lines) + "\n")
        components.append({"type":"preamble","name":"packages","path":"preamble/packages.tex","category":"package","description":"宏包"})

    # 3. 其余 preamble 行
    misc_lines = []
    skip = False
    for ln in plines:
        s = ln.strip()
        if s.startswith(r"\documentclass") or s.startswith(r"\usepackage"):
            continue
        misc_lines.append(ln.rstrip())

    if misc_lines:
        d = os.path.join(output_dir, "scripts", "components", "preamble")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "preamble-misc.tex"), "w", encoding="utf-8") as f:
            f.write("\n".join(misc_lines) + "\n")
        components.append({"type":"preamble","name":"preamble-misc","path":"preamble/preamble-misc.tex","category":"misc","description":"其余前导设置"})

    # manifest
    manifest = {"components": components, "version": "1.0.0"}
    mdir = os.path.join(output_dir, "scripts", "components")
    os.makedirs(mdir, exist_ok=True)
    with open(os.path.join(mdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[OK] 提取完成：{len(components)} 个组件")
    for c in components:
        print(f"  - {c['name']}: {c['path']}")

if __name__ == "__main__":
    main()
