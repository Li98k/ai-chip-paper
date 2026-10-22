# -*- coding: utf-8 -*-
"""R16-T9/E1: 列线分布电阻下的虚地残差与输出误差（redteam Q4，动摇 C1 的条目）

模型（显式假设，随输出声明）：
- W 条支路把电流 I_j=x_j·w_j/R0 汇入列线（电流模虚地拓扑，v5b 最终拓扑），
  列线金属每段有电阻 r_seg=ρ·pitch（ρ=线阻 Ω/mm，pitch=支路间距）。
  支路在距读出节点 (W-1-j)·pitch 处接入；读出节点由 BJT 虚地钳位，
  有限钳位阻抗用 R_vg 参数化（理想 0；无 R_E 跟随器 ~1/gm=500Ω@IC0=50µA；
  有 R_E 反馈 ~5Ω，v14/t3 环路增益口径）。
- 精确求解列线梯形网络节点电压（三对角 KCL，批式 Thomas），
  不假设"远端恒压"：支路 j 的实际电流 = (x_j - V_j)·w_j/R0。
- x_j∈[0,1) 均匀、w_j~N(0,0.02)（v16 口径）；误差归一化到理想输出电流的
  跨图案 RMS（v14 I_sig 口径的比值，无量纲）。
- 建立时间：τ_line≈R_col·C_col/3（分布 RC 梯形主极点近似），
  C_col 取 0.2pF/mm（显式假设）；支路建立 τ≈R_j·c_node（R_j~50MΩ, c~1fF→50ps）。
输出：误差 mean/p95/max vs（ρ、pitch、W、R_vg），列线预算核对单
（保住 INT8 量化噪声 0.4% 所允许的 ρ 上限），并与 redteam 推演的 26% 悲观角对照。
"""
import numpy as np

VREF_UNUSED = None  # 比值无量纲，x 用 [0,1) 归一（v16 口径）
R0 = 1e6
SW = 0.02           # w 的标准差（v16 同）
N_PAT = 300
SEEDS = 5

def thomas_batch(lo, di, up, rhs):
    """批式三对角求解: lo/di/up/rhs 形状 (n, m); lo[:,0]/up[:,-1] 未用."""
    n, m = rhs.shape
    cp = np.empty_like(up); dp = np.empty_like(rhs)
    cp[:, 0] = up[:, 0] / di[:, 0]
    dp[:, 0] = rhs[:, 0] / di[:, 0]
    for i in range(1, m):
        den = di[:, i] - lo[:, i] * cp[:, i-1]
        cp[:, i] = np.where(i < m-1, up[:, i] / den, 0.0)
        dp[:, i] = (rhs[:, i] - lo[:, i] * dp[:, i-1]) / den
    x = np.empty_like(rhs)
    x[:, -1] = dp[:, -1]
    for i in range(m-2, -1, -1):
        x[:, i] = dp[:, i] - cp[:, i] * x[:, i+1]
    return x

def run_coline(W, rho_ohm_mm, pitch_um, R_vg, n_pat=N_PAT, seed0=0):
    """返回 (err/I_rms 数组[n_pat*net], V_max[mV], R_col[Ω], C_col[pF])
    节点方程(KCL, 节点1..W 沿列线): 相邻段电导 1/r + 支路电导 g_j(有符号),
    仅节点1 额外经 Rhead=r+R_vg 到虚地(0V); I_read = V1/Rhead."""
    r = rho_ohm_mm * pitch_um / 1e3            # 每段线阻 Ω
    R_col = r * (W - 1)
    C_col = (pitch_um / 1e3) * W * 0.2         # pF (0.2pF/mm)
    Rhead = r + R_vg                            # 节点1 → 虚地
    g_inv = 1.0 / r
    errs = []
    vmax_mV = 0.0
    for s in range(seed0, seed0 + SEEDS):
        rng = np.random.default_rng(1000 + s)
        w = rng.standard_normal(W) * SW
        g = w / R0                              # 有符号支路电导
        X = rng.random((n_pat, W))
        I_id = X @ g                            # 理想 (虚地=0)
        lo = np.tile(-g_inv, (n_pat, W))
        di = np.tile(2.0 * g_inv, (n_pat, W))   #  interior: 两侧段
        di[:, 0] += 1.0 / Rhead - g_inv         #  节点1: 一侧段 + Rhead
        di[:, -1] -= g_inv                      #  节点W: 一侧段
        di += g                                 #  支路电导(有符号, |g|<<1/r)
        up = np.tile(-g_inv, (n_pat, W))
        rhs = X * g
        V = thomas_batch(lo, di, up, rhs)       # 节点 1..W 电压
        I_read = V[:, 0] / Rhead
        vmax_mV = max(vmax_mV, np.abs(V).max() * 1e3)
        I_rms = np.sqrt((I_id**2).mean())
        errs.append(np.abs(I_read - I_id) / I_rms)
    e = np.concatenate(errs)
    return e, vmax_mV, R_col, C_col

def cell(tag, **kw):
    e, vmax, Rcol, Ccol = run_coline(**kw)
    print(f"  {tag:34s} mean={e.mean()*100:7.3f}%  p95={np.percentile(e,95)*100:7.3f}%  "
          f"max={e.max()*100:7.2f}%  |V|max={vmax:.2f}mV  R_col={Rcol:.0f}Ω")
    return e

print("════ T9/E1 列线分布电阻误差（电流模虚地 + BJT 读出, v16 口径 x∈[0,1) w~N(0,0.02)）════")
print("A) 主矩阵: R_vg=理想0Ω, W=4096")
for rho in [1, 10, 100]:
    for pitch in [5, 10]:
        cell(f"W=4096 ρ={rho}Ω/mm pitch={pitch}µm", W=4096,
             rho_ohm_mm=rho, pitch_um=pitch, R_vg=0.0)
print("B) 有限虚地阻抗 (ρ=100Ω/mm, pitch=10µm, W=4096)")
for Rvg, why in [(0.0, "理想虚地"), (5.0, "R_E 反馈后 ~5Ω"), (500.0, "无R_E 1/gm@50µA")]:
    cell(f"R_vg={why}", W=4096, rho_ohm_mm=100, pitch_um=10, R_vg=Rvg)
print("C) W 标度 (ρ=100Ω/mm, pitch=10µm)")
for W in [256, 1024, 4096, 16384]:
    cell(f"W={W}", W=W, rho_ohm_mm=100, pitch_um=10, R_vg=0.0)
print("D) 列线预算: 找 p95≤0.4%(INT8 量化噪声) 的 ρ 上限 (pitch=10µm, W=4096)")
lo_, hi_ = 1.0, 1000.0
for _ in range(18):
    mid = np.sqrt(lo_ * hi_)
    e = run_coline(W=4096, rho_ohm_mm=mid, pitch_um=10, R_vg=0.0, n_pat=120)[0]
    if np.percentile(e, 95) > 0.004: hi_ = mid
    else: lo_ = mid
print(f"  ρ_max ≈ {lo_:.0f} Ω/mm (p95=0.4% 角, pitch=10µm, W=4096)")
e4096 = run_coline(W=4096, rho_ohm_mm=100, pitch_um=10, R_vg=0.0)[0]
e1024 = run_coline(W=1024, rho_ohm_mm=100, pitch_um=10, R_vg=0.0)[0]
print(f"  标度核对: p95(4096)/p95(1024)={np.percentile(e4096,95)/np.percentile(e1024,95):.2f} "
      f"(相干项预期≈(4096/1024)^1.5=8 附近: 列阻∝W 且累计电流∝√W → 误差∝W^1.5)")
Rcol = 100 * 10 / 1e3 * 4095
Ccol = 10 / 1e3 * 4096 * 0.2
print(f"E) 建立时间(悲观几何 ρ=100,pitch=10µm,W=4096): R_col={Rcol:.0f}Ω, "
      f"C_col={Ccol:.1f}pF, τ_line≈{Rcol*Ccol*1e-12/3*1e9:.1f}ns vs 100ns 节拍 (×2 MAC→20ns, 仍 <1/5)")
