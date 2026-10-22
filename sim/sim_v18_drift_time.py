# -*- coding: utf-8 -*-
"""R16-T9/E4: 漂移时间轴 × 重校准周期 → 末期最终余弦（redteam Q1/D1）

模型（v16 框架, 显式假设随输出声明）：
- 每单元失配随时间对数增长: ε_j(t)=ε_j(t0)·f(t), f(t)=1+κ·log10(t/t0),
  t0=出厂标定时刻(天)。κ 无实测(redteam Q1 声明: κ 无实测数据前任何仿真
  都是文献参数搬运)——本脚本把 κ 敏感性网格摆出来。
- 失配分两通道（t2_tol_wscale 的区分）:
  ① 独立通道 tol_ind ~ N(0,tol_ind): 享受 √W 统计抵消;
  ② 相干/梯度通道 grad_amp: 每权重矩阵行共享线性梯度 u_i=(i/n-0.5)*2,
     符号随机; 不享受抵消(0.87·tol·√W 类), 晶圆级梯度的工艺现实。
- 周期重校准把 ε(t0) 重抽并将 t 复位 → "重校准周期 T 天"的末期状态
  ≡ f(T) 放大后的失配分布 → 输出 T vs 末期最终余弦。
- 其余与 v16 逐调用对齐: 10 网络×20 MC×300 图案, BW=1.6MHz, ADC8,
  gmis±1%, tol=1%, grad=0, f=1 → 应与 v16-A 锚点 mean=0.8291 一致(自检)。
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

def run_net(seed, tol_ind=0.01, grad_amp=0.0, f=1.0):
    """随机数消耗顺序与 v16 run_one_net 对齐:
    每网络: Ws(L次 normal(shape)) → Xs(normal+random) → 每MC:
    每层 tol normal(shape) [grad 项在 tol 之后额外消耗, 仅 grad_amp>0] →
    gmis normal → 每层 噪声 normal."""
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
            eps = rng.normal(0, tol_ind, W.shape)      # v16 同位置消耗
            if grad_amp:
                n = W.shape[0]
                u = (np.arange(n)/max(n-1, 1) - 0.5) * 2.0
                eps = eps + grad_amp * rng.choice([-1.0, 1.0]) * np.abs(rng.standard_normal()) * u[:, None]
            Wt.append(W * (1 + f * eps))
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

def f_of(days, kappa):
    return 1.0 + kappa * np.log10(max(days, 1e-9))

def sweep(label, tol_ind, grad_amp, kappas, day_list):
    print(f"\n──── {label} ────")
    print("  重校准周期T(天): " + "".join(f"{d:>10g}" for d in day_list))
    for kap in kappas:
        row = []
        for d in day_list:
            f = f_of(d, kap)
            fins = np.concatenate([run_net(s, tol_ind, grad_amp, f) for s in range(N_NET)])
            row.append(fins.mean())
        print(f"  κ={kap:<5g} 末期余弦: " + "".join(f"{v:>10.4f}" for v in row))

if __name__ == "__main__":
    print("════ T9/E4 漂移时间轴 × 重校准周期 (v16 框架, 10网×20MC×300图案) ════")
    anchor = np.concatenate([run_net(s, 0.01, 0.0, 1.0) for s in range(N_NET)])
    print(f"锚点自检 (tol=1%,κ=0): mean={anchor.mean():.4f} (期望 0.8291, |Δ|={abs(anchor.mean()-0.8291):.4f})")
    assert abs(anchor.mean() - 0.8291) < 0.0005, "v16-A 锚点漂移"
    days = [1, 30, 90, 365, 730, 1825]
    sweep("① 仅独立失配 tol=1% (√W 抵消通道): κ ∈ {0.1, 0.3}",
          0.01, 0.0, [0.1, 0.3], days)
    sweep("② 独立 tol=1% + 相干梯度 grad=0.1% (t2 口径相干项量级): κ ∈ {0.1, 0.3}",
          0.01, 0.001, [0.1, 0.3], days)
    sweep("③ 独立 tol=1% + 相干梯度 grad=0.3%: κ ∈ {0.1, 0.3}",
          0.01, 0.003, [0.1, 0.3], days)
    sweep("④ 0.1% 工艺角 tol=0.1% 无梯度 (对照 C3 硬条件): κ ∈ {0.3}",
          0.001, 0.0, [0.3], days)
    print("\n注: f(T)=1+κ·log10(T天); κ=0.3 时 5 年(T=1825)放大 f=2.0。")
    print("注: κ 为文献区间参数搬运(无实测, redteam Q1), 结论按敏感性读, 不作锚点。")
