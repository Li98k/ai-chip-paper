# R16-T2 辅助脚本：容差统计红利的 W 标度实测复核
# 拓扑与误差模型与 sim_v5b C5 完全一致（电流模差分虚地，每支路 R 均匀扰动 ±tol），
# 改进三点以便做 W 标度研究：
#   (1) 每个样本重抽 x（v5b 固定单组 x，相对误差受单组 |Σwx| 抽样噪声影响大）；
#   (2) 报告"绝对误差 |ΔΣ|"（看 √W 标度）与"归一化误差 |ΔΣ|/‖wx‖₂"（看与 W 无关）；
#   (3) 相干最坏情况列用期望信号幅度（E|Σwx|=√(2W/3π)）消除分母抽样噪声。
# 理论预言：均匀 ±tol 的 σ=tol/√3；‖wx‖₂≈√(W/3)；|ΔΣ| 期望=σ‖wx‖₂·√(2/π)·?（MC 验证）；
#          归一化误差 RMS = tol/√3 = 0.577·tol，与 W 严格无关；
#          相干最坏/tol ≈ 0.866·√W。
import numpy as np

rng = np.random.default_rng(7)
R0 = 1e6
N = 400

def scan(W, tol, n=N):
    w = np.clip(rng.normal(0, 1.0, W), -4, 4)
    w_pos = np.clip(w, 0, None); w_neg = np.clip(-w, 0, None)
    with np.errstate(divide='ignore'):
        Rp = R0 / w_pos; Rn = R0 / w_neg
    abs_errs, rel_norm, rel_raw = [], [], []
    for _ in range(n):
        x = rng.uniform(0, 1.0, W)
        ideal = np.sum(w * x)
        Rp_m = Rp * (1 + rng.uniform(-tol, tol, W))
        Rn_m = Rn * (1 + rng.uniform(-tol, tol, W))
        Io = (np.sum(x / Rp_m) - np.sum(x / Rn_m)) * R0
        d = abs(Io - ideal)
        abs_errs.append(d)
        rel_norm.append(d / np.sqrt(np.sum((w * x) ** 2)))
        rel_raw.append(d / abs(ideal))
    abs_errs = np.array(abs_errs); rel_norm = np.array(rel_norm); rel_raw = np.array(rel_raw)
    wx_rms = np.sqrt(W / 3.0)                      # E‖wx‖₂ ≈ √(W·E[w²x²]) = √(W/3)
    coherent = tol * W * 0.399 / (np.sqrt(2 * W / (3 * np.pi)))  # tol·Σ|wx| / E|Σwx|
    return dict(abs_mean=abs_errs.mean(),
                abs_over_sqrtW=np.sqrt((abs_errs ** 2).mean()) / np.sqrt(W),  # RMS/√W
                norm_rms=np.sqrt((rel_norm ** 2).mean()),                    # 真 RMS
                raw_mean=rel_raw.mean(),
                raw_p95=np.percentile(rel_raw, 95),
                coherent=coherent, wx_rms=wx_rms)

print("T2: 容差误差的 W 标度（电流模差分虚地, MC 400 样本/点, 每样本重抽 x）")
print(f"{'W':>6} {'tol':>5} {'|ΔΣ|均值':>9} {'|ΔΣ|/√W':>8} {'‖wx‖₂理':>9} "
      f"{'归一RMS/tol':>11} {'相对mean%':>9} {'相对p95%':>8} {'相干/tol·√W':>11}")
for W in [256, 1024, 4096, 16384]:
    for tol in [0.01, 0.001]:
        r = scan(W, tol)
        print(f"{W:>6} {tol*100:>4.1f}% {r['abs_mean']:>9.2f} {r['abs_over_sqrtW']:>8.3f} "
              f"{r['wx_rms']:>9.1f} {r['norm_rms']/tol:>11.3f} "
              f"{r['raw_mean']*100:>9.3f} {r['raw_p95']*100:>8.3f} "
              f"{r['coherent']/(tol*np.sqrt(W)):>11.3f}")
print()
print("理论: |ΔΣ| = (tol/√3)·‖wx‖₂·√(2/π)? 见输出; 归一RMS/tol 应≈0.577=1/√3;")
print("      相干列应≈0.866 且与 W、tol 无关 → 相干误差/tol ∝ √W, 独立误差/tol = 常数。")
