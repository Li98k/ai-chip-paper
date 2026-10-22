# -*- coding: utf-8 -*-
"""R16-T7: 温度 × 1-f 噪声 × 权重漂移 对最终余弦的联合影响（基于 v16 框架）

模型口径（显式假设，逐条标注出处/理由）：
1) 温度 Tj=65/85/105°C → 热噪声电流功率 ∝ 4kT·BW·G，即幅度因子 √(T/300)。
   V_BE 漂移(-2mV/°C)与权重电阻共模温漂按 v13 与工程核对单 7 口径视为
   "一次性校准后抵消"，本仿真不重复计入（v13：共模漂移在 I=(1/R0)Σw·x 中
   精确抵消；V_BE 走带隙基准一次性校准）。
2) 1-f 噪声：corner 频率模型 S_1f(f)=S_white·f_c/f，从 f_L=1Hz（token 级
   积分窗 ~ms 量级）积到 BW，相对白噪声的功率增幅
        R_1f = f_c·ln(BW/f_L)/BW
   f_c 取 paper §4.5 对照表既有两条器件路线：BJT ~100Hz、MOS ~50kHz；
   off=理想无 1-f（crossbar 金属电阻本身 1-f 可忽略，项在读出管）。
   总噪声 σ ← σ_thermal·√(T/300)·√(1+R_1f)。
3) 权重漂移 tol=0/1/5%（乘法高斯，同 v16 C5 口径；5% 对应 v13-D 的
   ReRAM/浮栅离散度 3–10% 恶化档）。

框架与随机数消耗顺序与 sim_v16_depth_multiseed.py 逐调用对齐：
基线单元 (T=300K, 1-f off, tol=1%) 应与 v16-A 的 mean=0.8291 完全一致，
脚本自检该锚点。10 网络(≥8) × 20 MC × 300 图案，BW=1.6MHz(≈3.2MOPS)。
最坏单元另测恢复手段 BW=0.5MHz(=1MOPS, v10 权威 SNR=53.3dB)。
"""
import numpy as np

kB, q, VREF = 1.381e-23, 1.602e-19, 100e-3
R0 = 1e6
dims = [512, 1024, 1024, 1024, 512, 64]      # 同 v16: 6 层神经元 / 5 层权重矩阵
L = len(dims) - 1
N_PAT = 300; N_MC = 20; N_NET = 10
F_L = 1.0                                     # 1/f 积分下限 (Hz)
T_BASE = 300.0

def relu(z): return np.maximum(z, 0)
def quant(z, b):
    Vf = max(np.abs(z).max(), 1e-9); s = 2*Vf / 2**b
    return np.round(z/s)*s
def cos(a, b):
    return np.einsum('ij,ij->', a, b)/(np.linalg.norm(a)*np.linalg.norm(b))

def flicker_factor(BW, fc):
    """1-f 相对白噪声的噪声功率增幅 (1+R_1f)。fc=0 → 1。"""
    if fc <= 0: return 1.0
    return 1.0 + fc*np.log(BW/F_L)/BW

def run_one_net(BW, seed, T=T_BASE, fc=0.0, tol=0.01, adc=8):
    """随机数消耗顺序与 v16.run_one_net 完全一致（见模块 docstring 锚点自检）。"""
    rng = np.random.default_rng(seed)
    Ws = [rng.standard_normal((dims[i+1], dims[i]))*0.02 for i in range(L)]
    def dig_layers(X):
        outs = [X]
        for i in range(L):
            X = relu(X @ Ws[i].T); outs.append(X)
        return outs
    Xs = rng.random((N_PAT, dims[0]))
    Yref = dig_layers(Xs)
    layer_acc = np.zeros(L); finals = []
    noise_scale = np.sqrt(T/T_BASE)*np.sqrt(flicker_factor(BW, fc))
    for _ in range(N_MC):
        Wt = [W*(1+rng.normal(0, tol, W.shape)) for W in Ws]
        gmis = [rng.normal(0, 0.01) for _ in range(L)]
        X = Xs.copy()
        for i in range(L):
            z = X @ Wt[i].T
            Rnode = R0/np.abs(Ws[i]).sum(axis=1).mean()
            z = z + rng.normal(0, np.sqrt(4*kB*T_BASE*BW/Rnode)*R0/VREF*noise_scale, z.shape)
            z = z*(1+gmis[i])
            if adc: z = quant(z, adc)
            X = relu(z)
            layer_acc[i] += cos(X, Yref[i+1])
        finals.append(cos(X, Yref[-1]))
    return np.array(finals), layer_acc/N_MC

def cell(BW, T, fc, tol):
    fins, lays = [], []
    for s in range(N_NET):
        f, l = run_one_net(BW, s, T=T, fc=fc, tol=tol)
        fins.append(f); lays.append(l)
    return np.concatenate(fins), np.mean(lays, axis=0)

def tlabel(T): return f"{T-273.15:.0f}C" if T > 310 else f"{T:.0f}K"

if __name__ == "__main__":
    BW = 1.6e6   # ≈3.2MOPS/node（v16 基线吞吐）
    print(f"R16-T7 联合噪声矩阵 (L={L}, {N_NET}网络×{N_MC}MC×{N_PAT}图案, BW={BW/1e6:.1f}MHz≈3.2MOPS, ADC8)")
    print("  T 维度=热噪声√(T/300)（V_BE/电阻共模温漂按校准后抵消，见 docstring）")
    print("  1-f 维度=功率增幅 1+f_c·ln(BW/1Hz)/BW；f_c: BJT~100Hz / MOS~50kHz (paper §4.5 表)")
    print("="*100)

    # ---- 锚点自检: 应与 v16-A (0.8291) 完全一致 ----
    fin0, _ = cell(BW, T_BASE, 0.0, 0.01)
    d0 = abs(fin0.mean() - 0.8291)
    print(f"[锚点自检] T=300K,1-f off,tol=1%: mean={fin0.mean():.4f} (v16-A=0.8291, |Δ|={d0:.4f})"
          f" {'OK' if d0 < 0.001 else 'MISMATCH'}")

    T_list = [T_BASE, 338.15, 358.15, 378.15]           # 25(基线)/65/85/105°C
    fc_list = [("off", 0.0), ("BJT100", 100.0), ("MOS50k", 50e3)]
    tol_list = [0.0, 0.01, 0.05]

    print("\n[联合矩阵] 最终层余弦 mean(std)，行=tol，列=T×1-f：")
    hdr = "  tol\\cell  " + " ".join(f"{tlabel(T)}|{fn:<7s}" for T in T_list for fn, _ in fc_list)
    print(hdr)
    grid = {}
    for tol in tol_list:
        row = []
        for T in T_list:
            for fn, fc in fc_list:
                fin, _ = cell(BW, T, fc, tol)
                grid[(tol, T, fn)] = fin
                row.append(f"{fin.mean():.4f}({fin.std():.3f})")
        print(f"  tol={tol:<6.1%} " + " ".join(f"{c:<14s}"[:14] for c in row))

    # ---- 单因子归因（相对基线 300K/off/1%）----
    base = grid[(0.01, T_BASE, "off")].mean()
    print(f"\n[单因子归因] 相对基线 {base:.4f} 的余弦跌幅（另两因子留在基线位）：")
    print("  温度单开   : " + "  ".join(
        f"{tlabel(T)}: {base-grid[(0.01,T,'off')].mean():+.4f}" for T in T_list[1:]))
    print("  1-f 单开   : " + "  ".join(
        f"{fn}: {base-grid[(0.01,T_BASE,fn)].mean():+.4f}" for fn, _ in fc_list[1:]))
    print("  漂移单开   : " + "  ".join(
        f"tol={tol:.0%}: {base-grid[(tol,T_BASE,'off')].mean():+.4f}" for tol in tol_list if tol != 0.01))

    # ---- 交互性检验：联合跌幅 vs 单因子跌幅之和 ----
    print("\n[交互性] 联合跌幅 ÷ 单因子跌幅之和（≈1 即近可加，>1 超可加）：")
    for T in T_list[1:]:
        for fn in ("BJT100", "MOS50k"):
            for tol in (0.05,):
                joint = base - grid[(tol, T, fn)].mean()
                solo = ((base - grid[(0.01, T, "off")].mean())
                        + (base - grid[(0.01, T_BASE, fn)].mean())
                        + (base - grid[(tol, T_BASE, "off")].mean()))
                r = joint/solo if solo > 1e-9 else float('nan')
                print(f"  {tlabel(T)}+{fn}+tol5%: 联合跌幅={joint:.4f}, 单因子和={solo:.4f}, 比值={r:.2f}")

    # ---- 最坏单元 + 恢复手段 ----
    worst_key = min(grid, key=lambda k: grid[k].mean())
    wk = f"tol={worst_key[0]:.0%}/{tlabel(worst_key[1])}/{worst_key[2]}"
    wf, wlay = cell(BW, worst_key[1], dict(fc_list)[worst_key[2]], worst_key[0])
    rf, rlay = cell(0.5e6, worst_key[1], dict(fc_list)[worst_key[2]], worst_key[0])
    print(f"\n[最坏单元] {wk}: mean={wf.mean():.4f} std={wf.std():.4f} "
          f"range=[{wf.min():.4f},{wf.max():.4f}]")
    print("   逐层: " + " ".join(f"L{i+1}={wlay[i]:.4f}" for i in range(L)))
    print(f"[恢复手段] 最坏单元降 BW=0.5MHz(=1MOPS): mean={rf.mean():.4f} std={rf.std():.4f}")
    print("   逐层: " + " ".join(f"L{i+1}={rlay[i]:.4f}" for i in range(L)))
    print(f"   → 恢复幅度 {wf.mean():.4f} → {rf.mean():.4f}"
          f"（对照 v16 干净基线恢复 0.8291→0.9281）")
