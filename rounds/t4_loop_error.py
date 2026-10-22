# -*- coding: utf-8 -*-
"""R16-T4: 层间闭环链的逐层误差传播机制分解
背景: 第 4 章的闭环链 = ①电压→电流 ②电流求和 ③读出 ④ADC/DAC 每层重复一次。
v16 已标定累积分布 (最终余弦 0.829±0.024 @3.2MOPS, 1MOPS 恢复 0.928), 但其逐层
衰减为何呈 ~4~6×/层的复合增速没有机制解释。本脚本把 v16-A 模型分解成可测量:
  A 逐层量分解: 注入噪声绝对 RMS σ_k、理想信号 RMS、相对噪声 ε_k、实测 1-cos、
    闭合式核对 cos≈1/√(1+ε²)
  B 单层注入: 只在第 k 层注入热噪声 (tol=0,gmis=0,ADC8), 测 (1-cos) 逐层传播
    → 存量误差的复合因子 (预期 ≈1, 即不放大) 与注入位置敏感度行向量
  C 深链代数恒等: 30 级 mV→nA→mV 单位往返 (无噪声/无ADC/无容差), 拓扑深度罚
  D 量化预算: 逐层 8bit 量化噪声 vs 热噪声绝对值
  E 模型变体探索 (不改 v16 权威口径): 数字域逐层满摆幅 rescale 是否切断
    "信号收缩×绝对恒定噪声" 的复合项
框架与常数完全沿用 sim_v16_depth_multiseed.py (dims, W~N(0,0.02), BW=1.6MHz,
tol=1%, ADC8, 逐层读出增益失配 gmis±1%, 噪声模型 σ=√(4kT·BW/Rnode)·R0/VREF)。
"""
import numpy as np

kB, T, VREF = 1.381e-23, 300, 100e-3
R0 = 1e6
dims = [512, 1024, 1024, 1024, 512, 64]      # 6 神经元层 / 5 权重层 (v16 同)
L = len(dims) - 1
N_PAT = 300; N_MC = 20; N_NET = 5
BW = 1.6e6                                    # v16-A: ≈3.2MOPS/node

def relu(z): return np.maximum(z, 0)
def quant(z, b):
    Vf = max(np.abs(z).max(), 1e-9); s = 2*Vf / 2**b
    return np.round(z/s)*s
def cos(a, b):
    return np.einsum('ij,ij->', a, b)/(np.linalg.norm(a)*np.linalg.norm(b))

def sigma_noise(W):
    """v16 噪声模型: 节点等效电导 G=1/Rnode 的热噪声折到 ADC 归一化单位."""
    Rnode = R0/np.abs(W).sum(axis=1).mean()
    return np.sqrt(4*kB*T*BW/Rnode)*R0/VREF

def make_net(seed):
    rng = np.random.default_rng(seed)
    Ws = [rng.standard_normal((dims[i+1], dims[i]))*0.02 for i in range(L)]
    Xs = rng.random((N_PAT, dims[0]))
    return rng, Ws, Xs

def ideal(Ws, Xs):
    """数字参考 (含 relu); 返回逐层输出 [X0, Y1..YL]."""
    outs = [Xs]
    for i in range(L):
        Xs = relu(Xs @ Ws[i].T); outs.append(Xs)
    return outs

def analog(Ws, Xs, rng, noise_layers: "int | str" = 'all', tol=0.01, adc=8,
           gmis=0.01, rescale=False):
    """一次模拟级联; noise_layers='all'/k/None; rescale=数字域逐层满摆幅复位
    (×正常数, relu/矩阵乘可交换, cos 不变, 参考无需重标)."""
    Yref = ideal(Ws, Xs)
    Wt = [W*(1+rng.normal(0, tol, W.shape)) for W in Ws] if tol else Ws
    X = Xs.copy(); lay = []
    for i in range(L):
        z = X @ Wt[i].T
        if noise_layers == 'all' or noise_layers == i:
            z = z + rng.normal(0, sigma_noise(Ws[i]), z.shape)
        if gmis: z = z*(1+rng.normal(0, gmis))
        if adc: z = quant(z, adc)
        X = relu(z)
        if rescale: X = X*(1.0/max(X.max(), 1e-12))
        lay.append(cos(X, Yref[i+1]))
    return lay

if __name__ == "__main__":
    print(f"R16-T4 闭环链误差传播机制分解 (v16 框架: {N_NET}网络×{N_MC}MC×{N_PAT}图案, "
          f"tol=1%, ADC8, gmis±1%, BW={BW/1e6}MHz)")
    print("="*84)

    # ---- A: v16-A 基线 + 逐层量分解 ----
    nets = [make_net(s) for s in range(N_NET)]
    lay_acc = np.zeros(L); sig_rms = np.zeros(L); sig_max = np.zeros(L)
    sigm = np.zeros(L)
    for rng, Ws, Xs in nets:
        Zid = [Xs]
        for i in range(L): Zid.append(Zid[-1] @ Ws[i].T)
        for i in range(L):
            sig_rms[i] += Zid[i].std(); sig_max[i] += np.abs(Zid[i]).max()
            sigm[i] += sigma_noise(Ws[i])
        for _ in range(N_MC):
            lay_acc += np.array(analog(Ws, Xs, rng))
    lay = lay_acc/(N_NET*N_MC); sig_rms /= N_NET; sig_max /= N_NET; sigm /= N_NET
    eps = sigm/sig_rms
    print("[A] v16-A 基线 (最终层 cos mean=%.4f, 期望≈0.829±0.024 的 5 网络抽样)" % lay[-1])
    print("    层   σ噪声(归一)  信号RMS   ε=σ/RMS   1-cos实测  1-cos逐层倍率  闭合式1/√(1+ε²)")
    for i in range(L):
        r = "" if i == 0 else f"{(1-lay[i])/(1-lay[i-1]):6.2f}"
        print(f"   L{i+1}   {sigm[i]:9.5f} {sig_rms[i]:9.4f} {eps[i]*100:8.1f}% "
              f"{1-lay[i]:9.4f} {r:>12}   {1/np.sqrt(1+eps[i]**2):9.4f}")

    # ---- B: 单层注入 (纯热噪声, tol/gmis 关) ----
    print("\n[B] 单层注入热噪声 (仅第 k 层; tol=0, gmis=0, ADC8) — 注入位置敏感度")
    print("    注入层k  最终1-cos   (1-cos) 逐层轨迹 (注入层→末层)")
    for k in range(L):
        acc = np.zeros(L)
        for rng, Ws, Xs in nets:
            for _ in range(N_MC):
                acc += np.array(analog(Ws, Xs, rng, noise_layers=k, tol=0, gmis=0))
        lc = acc/(N_NET*N_MC)
        traj = "  ".join(f"L{i+1}:{1-lc[i]:.4f}" for i in range(k, L))
        ratios = [ (1-lc[i+1])/(1-lc[i]) for i in range(k, L-1) ]
        rr = np.mean(ratios) if ratios else float('nan')
        print(f"     L{k+1}    {1-lc[-1]:8.4f}    {traj}   传播倍率/层≈{rr:.2f}")

    # ---- C: 深链代数恒等 (mV→nA→mV 单位往返 30 级) ----
    print("\n[C] 30 级级联 'R=R0/w 布线→虚地求和→读出 R_L=R0' 的单位往返恒等 (无噪声/ADC/容差)")
    rngc = np.random.default_rng(123)
    z_a = rngc.random(64)*0.1          # 输入电压 (V, 0~100mV)
    z_d = z_a.copy()
    worst = 0.0
    for _ in range(30):
        Wc = rngc.standard_normal((64, 64))*0.02
        I = (Wc @ z_a)/R0              # 电压→电流 (nA 量级)
        z_a = I*R0                     # 读出 R_L=R0 → 电压 (模拟链)
        z_d = Wc @ z_d                 # 数字参考
        z_a = z_a/max(z_a.max(), 1e-30)   # 逐层摆幅复位 (×正常数, 精确)
        z_d = z_d/max(z_d.max(), 1e-30)
        worst = max(worst, np.max(np.abs(z_a-z_d))/np.max(np.abs(z_d)))
    print(f"    30 级最坏相对误差 = {worst:.2e}   (纯浮点; 域转换拓扑自身深度罚 ≈ 0)")

    # ---- D: 量化预算 vs 热噪声 ----
    print("\n[D] 逐层 8bit 量化噪声 vs 热噪声 (绝对量, 归一化单位; v16 同摆幅)")
    print("    层   max|z|    量化步s=2max/256   量化噪声≈s/√12   热噪声σ   量化/热")
    for i in range(L):
        s = 2*sig_max[i]/256; qn = s/np.sqrt(12)
        print(f"   L{i+1}  {sig_max[i]:8.4f} {s:14.5f} {qn:16.5f} {sigm[i]:10.5f} {qn/sigm[i]:7.2f}")

    # ---- E: 变体 — 数字域逐层满摆幅 rescale ----
    print("\n[E] 模型变体 (不改 v16 权威口径): 数字岛逐层 ×(1/max) 满摆幅复位")
    layE = np.zeros(L)
    for rng, Ws, Xs in nets:
        for _ in range(N_MC):
            layE += np.array(analog(Ws, Xs, rng, rescale=True))
    layE /= N_NET*N_MC
    print("    逐层 1-cos: " + " ".join(f"L{i+1}:{1-layE[i]:.4f}" for i in range(L)))
    print(f"    最终余弦: 无rescale {lay[-1]:.4f} → 有rescale {layE[-1]:.4f}")

    # ---- F: 误差源归因 (全链注入, 单开每个误差源; 有/无 rescale 两遍) ----
    print("\n[F] 误差源归因: 单开一个源跑全链 (最终层余弦 mean)")
    variants = [
        ("仅热噪声",   dict(noise_layers='all', tol=0,    gmis=0,    adc=0)),
        ("仅容差1%",   dict(noise_layers=None,  tol=0.01, gmis=0,    adc=0)),
        ("仅增益失配", dict(noise_layers=None,  tol=0,    gmis=0.01, adc=0)),
        ("仅ADC8",     dict(noise_layers=None,  tol=0,    gmis=0,    adc=8)),
        ("全开(v16-A)",dict(noise_layers='all', tol=0.01, gmis=0.01, adc=8)),
    ]
    print("    变体          无rescale   有rescale")
    for name, kw in variants:
        f0 = []; f1 = []
        for rng, Ws, Xs in nets:
            for _ in range(N_MC):
                f0.append(analog(Ws, Xs, rng, **kw)[-1])
                f1.append(analog(Ws, Xs, rng, rescale=True, **kw)[-1])
        print(f"    {name:<12}  {np.mean(f0):9.4f}   {np.mean(f1):9.4f}")
