# -*- coding: utf-8 -*-
"""R16-T9/E2: 单元级缺陷注入——stuck-open 与 stuck-at-worst 对最终余弦的影响
(redteam Q5: 270 亿单元 1ppm = 2.7 万坏权重, 模拟权重无 ECC)

模型（v16 框架逐调用对齐, 显式假设随输出声明）:
- 缺陷在两通道注入(每 MC 重抽, 模拟"哪颗芯片哪些单元坏"):
  ① stuck-open: 概率 p_open, w→0(项丢失, 等价 w=-W 全消);
  ② stuck-at-worst: 概率 p_worst, w→±max|w_row|(行内最大幅, 符号随机,
     最坏错权重; 这是悲观口径——真实 stuck-at 电平未必是行最大)。
- 其余与 v16 run_one_net 完全一致(10 网×20MC×300 图案, BW=1.6MHz,
  tol=1%, ADC8, gmis±1%); p=0 单元应与 v16-A 锚点 0.8291 一致(自检)。
- 输出"可容忍缺陷率": 找 final mean≥0.9(v16-B 恢复档水平)与 ≥0.8291-0.02
  (INT8 3.2MOPS 档减 1σ)的 p 上限。
随机数消耗: 每层 tol normal 之后额外消耗 2 次(size=shape, 仅 p>0),
不扰动 p=0 锚点路径。
"""
import numpy as np

kB, T, VREF = 1.381e-23, 300, 100e-3
R0 = 1e6
dims = [512, 1024, 1024, 1024, 512, 64]
L = len(dims) - 1
N_PAT = 300; N_MC = 20; N_NET = 10
BW = 1.6e6

def relu(z): return np.maximum(z, 0)
def quant(z, b):
    Vf = max(np.abs(z).max(), 1e-9); s = 2*Vf / 2**b
    return np.round(z/s)*s
def cos(a, b):
    return np.einsum('ij,ij->', a, b)/(np.linalg.norm(a)*np.linalg.norm(b))

def run_net(seed, p_open=0.0, p_worst=0.0):
    rng = np.random.default_rng(seed)
    Ws = [rng.standard_normal((dims[i+1], dims[i]))*0.02 for i in range(L)]
    def dig_layers(X):
        outs = [X]
        for i in range(L):
            X = relu(X @ Ws[i].T); outs.append(X)
        return outs
    Xs = rng.random((N_PAT, dims[0]))
    Yref = dig_layers(Xs)
    finals = []
    for _ in range(N_MC):
        Wt = []
        for W in Ws:
            Wd = W * (1 + rng.normal(0, 0.01, W.shape))
            if p_open:
                mask = rng.random(W.shape) < p_open
                Wd = np.where(mask, 0.0, Wd)
            if p_worst:
                mask = rng.random(W.shape) < p_worst
                wmax = np.abs(W).max(axis=1, keepdims=True)
                worst = wmax * rng.choice([-1.0, 1.0], size=W.shape)
                Wd = np.where(mask, worst, Wd)
            Wt.append(Wd)
        gmis = [rng.normal(0, 0.01) for _ in range(L)]
        X = Xs.copy()
        for i in range(L):
            z = X @ Wt[i].T
            Rnode = R0/np.abs(Ws[i]).sum(axis=1).mean()
            z = z + rng.normal(0, np.sqrt(4*kB*T*BW/Rnode)*R0/VREF, z.shape)
            z = z*(1+gmis[i])
            z = quant(z, 8)
            X = relu(z)
        finals.append(cos(X, Yref[-1]))
    return np.array(finals)

def sweep(tag, **kw):
    fins = np.concatenate([run_net(s, **kw) for s in range(N_NET)])
    print(f"  {tag:38s} mean={fins.mean():.4f} std={fins.std():.4f} "
          f"min={fins.min():.4f} p5={np.percentile(fins,5):.4f}")
    return fins

if __name__ == "__main__":
    print("════ T9/E2 单元缺陷注入 (v16 框架, 10网×20MC×300图案) ════")
    a = sweep("锚点 p=0", p_open=0.0, p_worst=0.0)
    assert abs(a.mean() - 0.8291) < 0.0005, f"v16-A 锚点漂移 {a.mean():.4f}"
    print(f"  锚点自检: {a.mean():.4f} vs 0.8291 ✓")
    print("① stuck-open (w→0, 项丢失):")
    N_CELLS = sum(dims[i+1]*dims[i] for i in range(L))   # 仿真阵列总单元数
    for p in [1e-6, 1e-4, 1e-2, 5e-2]:
        sweep(f"p_open={p:g} (仿真阵列≈{p*N_CELLS:.0f}坏/次)", p_open=p)
    print("② stuck-at-worst (w→±行最大幅, 悲观):")
    for p in [1e-6, 1e-4, 1e-2]:
        sweep(f"p_worst={p:g}", p_worst=p)
    print("③ 混合 p_open=p_worst=p:")
    for p in [1e-4, 1e-2]:
        sweep(f"p={p:g} 双通道", p_open=p, p_worst=p)
    # 可容忍缺陷率: 二分到 mean≥0.8291-0.02 (基线-1σ)
    lo_, hi_ = 0.0, 1.0
    for _ in range(16):
        mid = (lo_ + hi_) / 2
        f = np.concatenate([run_net(s, p_open=mid) for s in range(3)])
        if f.mean() >= 0.809: lo_ = mid
        else: hi_ = mid
    print(f"④ 可容忍 stuck-open 率(mean≥0.809≈基线−1σ): p*≈{lo_:.1e} "
          f"(27B 全片折算 ≈{lo_*27e9:.3g} 坏单元; 1ppm 角对照见上)")
