#!/usr/bin/env python3
"""R16 一致性门禁：扫禁用旧数字 + 复跑 sim_v11 恒等式。--full 再复跑 v5b/v10/v16。"""
import re, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv/bin/python")

BANNED = [
    (r"2\.56\s*mA", "sim_v5 旧值 2.56mA（现口径 1.10mA 倒灌/−0.02mA 残差）"),
    (r"1\.32\s*%", "C5 旧值 1.32%（现口径 mean 0.54/p95 1.31）"),
    (r"NorthPole \(Shafiee", "ISAAC/NorthPole 混淆未勘误"),
    (r"158\s*TOPS/W", "无出处 158 TOPS/W"),
    (r"HPCA 2016\s*/\s*NorthPole", "文献3 旧混引"),
    (r"ADC 136\s*nJ", "v12 旧单位错 136nJ（应 pJ）"),
    (r"最终\s*0\.79(?!1)", "旧单点 0.79（应 v16: 0.829±0.024）"),
    (r"final\s+0\.79(?!1)", "old single-point 0.79"),
    (r"@ ?10 ?MOPS[:：] ?0\.79", "旧 0.79@10MOPS 口径"),
    (r"6\.4e10 TOPS|6\.4 ?× ?10\^?10", "v12 TOPS 平方 bug 残留"),
]
DOCS = ["paper.md", "paper_en.md", "README.md"]
# 勘误说明行允许提及旧值（含"勘误/旧稿/无出处已删/应/现口径"字样或位于 erratum 上下文）
ALLOW_WORDS = ("勘误", "旧稿", "旧值", "无出处已删", "erratum", "removed", "此前", "现口径", "应 pJ", "误")

def scan_docs():
    bad = 0
    for d in DOCS:
        p = ROOT / d
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for pat, why in BANNED:
                if re.search(pat, line) and not any(w in line for w in ALLOW_WORDS):
                    print(f"  STALE {d}:{i}: {why}\n    > {line.strip()[:120]}")
                    bad += 1
    return bad

def run_sim(name, needle, timeout=600):
    try:
        out = subprocess.run([PY, f"sim/{name}"], capture_output=True, text=True,
                             timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        print(f"  FAIL {name}: timeout")
        return 1
    if needle not in out.stdout:
        print(f"  FAIL {name}: 输出缺少锚点 {needle!r}")
        print("     tail:", out.stdout[-200:].replace("\n", " | "))
        return 1
    print(f"  ok   {name}")
    return 0

def main():
    full = "--full" in sys.argv
    print("[1/3] 文档禁用旧数字扫描 ...")
    bad = scan_docs()
    print("     CLEAN" if bad == 0 else f"     {bad} 处过期")
    print("[2/3] 恒等式复跑 sim_v11 (期望 1e-16 级) ...")
    rc = run_sim("sim_v11_3layer.py", "1.16e-16")
    if full:
        print("[3/3] 全量复跑 v5b/v10/v16/v12 ...")
        rc += run_sim("sim_v5b.py", "0.1%")
        rc += run_sim("sim_v10_snr_mc.py", "SNR", 900)
        rc += run_sim("sim_v16_depth_multiseed.py", "mean", 1800)
        rc += run_sim("sim_v12_qwen27b.py", "TOPS")
    print("VERDICT:", "CLEAN" if bad + rc == 0 else "DIRTY")
    sys.exit(0 if bad + rc == 0 else 1)

if __name__ == "__main__":
    main()
