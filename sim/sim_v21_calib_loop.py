# -*- coding: utf-8 -*-
"""R16-T9/E3: 空间相关失配场 + 理想化全单元标定的残差闭环（redteam Q2）

三步（redteam Q2 工单原文）: 注入空间相关失配场(独立+梯度混合) →
理想化全单元标定(q 比特测读)后残差 → 最终余弦。
回答"标定把梯度失配压掉多少、需要多少比特精度"。

模型（v16 框架逐调用对齐, 显式假设随输出声明）:
- 失配场 ε_j = tol_ind·N(0,1) + grad·|N(0,1)|·u_row·±1
  （行共享线性梯度 u∈[-1,1], t2_tol_wscale 相干通道同口径;
   grad=0.1%/0.3% = 晶圆级梯度工艺现实档）
- 标定 = 流片后逐单元测读 ε, q 比特 ADC 量化(满量程 ±4σ_ε) + 测读噪声
  (½LSB 高斯)；编程侧补偿 W̃=W·(1+ε)·(1-ε̂)≈W·(1+ε-ε̂)。
  "理想标定" = q=∞ 且无测读噪声(残差 0)。
- 标定不触及热噪声/ADC/增益失配(v16 其余项原样保留)。
- tol_ind=1%、grad=0、不标定 应与 v16-A 锚点 0.8291 一致(自检)。
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

def run_net(seed, tol_ind=0.01, grad=0.0, calib=None):
    """calib=None 不标定 / 'ideal' / q(比特数)"""
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
            eps = rng.normal(0, tol_ind, W.shape)
            if grad:
                n = W.shape[0]
                u = (np.arange(n)/max(n-1, 1) - 0.5) * 2.0
                eps = eps + grad * rng.choice([-1.0, 1.0]) * np.abs(rng.standard_normal()) * u[:, None]
            if calib == 'ideal':
                eps_eff = np.zeros_like(eps)
            elif calib is not None:
                sig = np.sqrt(tol_ind**2 + grad**2)      # 场总 σ (近似口径)
                delta = 8*sig / 2**calib                  # 满量程 ±4σ
                meas = eps + rng.normal(0, delta/np.sqrt(12), eps.shape)
                eps_eff = eps - np.round(meas/delta)*delta
            else:
                eps_eff = eps
            Wt.append(W * (1 + eps_eff))
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

def cell(tag, **kw):
    fins = np.concatenate([run_net(s, **kw) for s in range(N_NET)])
    print(f"  {tag:44s} mean={fins.mean():.4f} std={fins.std():.4f}")
    return fins.mean()

if __name__ == "__main__":
    print("════ T9/E3 相关失配场 + q 比特标定残差 (v16 框架) ════")
    a = cell("锚点自检 tol=1% grad=0 不标定", tol_ind=0.01, grad=0.0)
    assert abs(a - 0.8291) < 0.0005, f"v16-A 锚点漂移 {a:.4f}"
    print(f"  vs 0.8291 ✓")
    for grad, gtag in [(0.0, "grad=0"), (0.001, "grad=0.1%"), (0.003, "grad=0.3%")]:
        print(f"──── {gtag} (独立 tol=1% 之上叠加行共享梯度) ────")
        cell("不标定", grad=grad)
        for q in [3, 4, 6, 8]:
            cell(f"标定 q={q}bit (±4σ 满量程)", grad=grad, calib=q)
        cell("理想标定 (残差=0)", grad=grad, calib='ideal')
    print("注: 标定只消静态失配场, 不消热噪声/ADC/增益失配 →")
    print("    '理想标定'行 ≈ v16 去掉 tol 通道的天花板; q≥6 已贴天花板。")
