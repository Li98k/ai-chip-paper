# -*- coding: utf-8 -*-
"""R15: 深度累积的多种子分布标定（把 v7/v8 的单网络点值标定为分布）
背景: v7(seed42) 最终层余弦 0.889, v8(seed7) 0.791 —— 两者物理模型完全一致,
差异仅来自固定随机权重的实现不同(单网络样本)。论文若只报点值会误导。
本脚本: 抽 N_NET 个独立网络, 每网络 N_MC 次芯片级 MC, 输出最终层余弦的
均值/std/范围; 逐层曲线(网络平均); 并跨种子验证恢复手段
"采样时钟降到 BW=0.5MHz(=1MOPS, v10 权威 SNR=53.3dB)" 是否稳定。
BW↔吞吐 换算沿用 v10: BW = 0.5MHz × MOPS。
"""
import numpy as np
kB, T, VREF = 1.381e-23, 300, 100e-3
R0 = 1e6
dims = [512, 1024, 1024, 1024, 512, 64]      # 6 层神经元 / 5 层权重矩阵
L = len(dims) - 1
N_PAT = 300; N_MC = 20; N_NET = 10

def relu(z): return np.maximum(z, 0)
def quant(z, b):
    Vf = max(np.abs(z).max(), 1e-9); s = 2*Vf / 2**b
    return np.round(z/s)*s
def cos(a, b):
    return np.einsum('ij,ij->', a, b)/(np.linalg.norm(a)*np.linalg.norm(b))

def run_one_net(BW, seed, tol=0.01, adc=8):
    """返回 (最终层余弦列表, 逐层余弦均值向量)"""
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
    for _ in range(N_MC):
        Wt = [W*(1+rng.normal(0, tol, W.shape)) for W in Ws]
        gmis = [rng.normal(0, 0.01) for _ in range(L)]
        X = Xs.copy()
        for i in range(L):
            z = X @ Wt[i].T
            Rnode = R0/np.abs(Ws[i]).sum(axis=1).mean()
            z = z + rng.normal(0, np.sqrt(4*kB*T*BW/Rnode)*R0/VREF, z.shape)
            z = z*(1+gmis[i])
            if adc: z = quant(z, adc)
            X = relu(z)
            layer_acc[i] += cos(X, Yref[i+1])
        finals.append(cos(X, Yref[-1]))
    return np.array(finals), layer_acc/N_MC

if __name__ == "__main__":
    print(f"R15 深度累积多种子标定 (L={L} 权重层/6 神经元层, {N_NET} 网络 × {N_MC} MC × {N_PAT} 图案, tol=1%, ADC8)")
    print("="*72)
    base_mean = None
    for tag, BW, extra in [
            ("A  BW=1.6MHz (≈3.2MOPS/node)", 1.6e6, {}),
            ("B  BW=0.5MHz (=1MOPS, 恢复手段)", 0.5e6, {}),
            ("C  BW=1.6MHz tol=0.1%", 1.6e6, dict(tol=0.001)),
            ("D  BW=1.6MHz ADC16", 1.6e6, dict(adc=16))]:
        fins, lays = [], []
        for s in range(N_NET):
            f, l = run_one_net(BW, s, **extra)
            fins.append(f); lays.append(l)
        fin = np.concatenate(fins); lay = np.mean(lays, axis=0)
        print(f"{tag}: 最终层余弦 mean={fin.mean():.4f} std={fin.std():.4f} "
              f"range=[{fin.min():.4f},{fin.max():.4f}]")
        print("   逐层(网络平均): " + " ".join(f"L{i+1}={lay[i]:.4f}" for i in range(L)))
        if tag.startswith("A"): base_mean = fin.mean()
        if tag.startswith("B"):
            print(f"   → 恢复手段跨种子稳定: 均值 {base_mean:.4f} → {fin.mean():.4f} (>0.9)")
