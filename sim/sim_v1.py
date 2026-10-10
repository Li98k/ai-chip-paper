"""R0 核心仿真 v1：三极管放大 + 参数即电阻 的 AI 芯片方案
电路模型（用户设想的形式化）：
  上一层 j=1..W 个神经元输出电压 x_j（0..Vmax，非负部分）
  每路经电阻 R_j = R0 / w_j（电导映射 G_j = w_j/R0）连到三极管 Q 基极 B
  发射极经 R_E 到地，集电极经 R_C 到 VCC
  期望：I_C ∝ Σ w_j x_j
本脚本量化四件事：
  A. 基极节点直流工作点的非线性度（Ebers-Moll 精确解 vs 理想线性）
  B. 噪声 → SNR / 有效位数（热噪声 + 散粒噪声）
  C. 电阻容差（1% / 0.1%）→ 计算误差（Monte Carlo）
  D. 60 层级联时 β 增益累积（是否必须逐层归一化）
"""
import numpy as np

q = 1.602e-19
kB = 1.381e-23
T = 300.15
VT = kB * T / q          # 25.9 mV
BETA = 100.0
VCC = 1.0                # 低压节点设计
R0 = 40e3                # 基准电阻（电导映射 R = R0/w）
W = 4096                 # 扇入
R_E = 50.0               # 发射极电阻（负反馈线性化）
R_C = 2e3                # 集电极负载

def ic_of_vb(vb, rng_x, Rw):
    """给定基极节点电压 vb 与各路输入电压 rng_x、电阻 Rw，用 Ebers-Moll 求 I_C。
    基极节点单未知数 KCL：Σ_j (x_j - vb)/R_j = I_B(vb)
    I_B 经 Ebers-Moll 全模型（含 Early 效应）表达为 V_BE 的函数。"""
    VBE = vb             # 发射极经 R_E：先迭代
    for _ in range(80):
        VBE = vb - (1.0 + 1.0 / BETA) * _ic_be(VBE) * R_E  # 初值迭代
    # Ebers-Moll（正向为主，忽略反向穿透）
    Ic = BETA * VT / (R_E * (1 + 1e-9)) * 0  # placeholder
    # 正确做法：直接解 I_E 方程。I_E = I_S*(exp(VBE/VT)-1) * (1+VCE/VA) 近似
    # 这里用传输电流：I_F = I_S*(exp(VBE/VT)-1); I_C = αF*I_F*(1+VCE/VA); I_B = I_F - I_C*... 
    # 简化自洽模型：
    IS = 1e-14
    VA = 100.0
    # 迭代 VBE 使 KCL 闭合
    Vbe = vb
    for _ in range(200):
        IF = IS * (np.exp(np.clip(Vbe, -0.3, 0.9) / VT) - 1.0)
        IC = BETA / (BETA + 1) * IF
        IB = IF - IC
        IE = IF
        # 发射极节点：Vbe = vb - IE*R_E
        Vbe_new = vb - IE * R_E
        if abs(Vbe_new - Vbe) < 1e-12:
            Vbe = Vbe_new
            break
        Vbe = Vbe_new
    IF = IS * (np.exp(np.clip(Vbe, -0.3, 0.9) / VT) - 1.0)
    IC = BETA / (BETA + 1) * IF * (1.0 + 0.3 / VA)  # VCE 中等 → Early 小修正
    return IC, Vbe

def _ic_be(vbe):
    IS = 1e-14
    return BETA / (BETA + 1) * IS * (np.exp(np.clip(vbe, -0.3, 0.9) / VT) - 1.0)

def solve_node(vbias, x, Rw, Rbias):
    """基极节点电压求解：Σ (x_j - vb)/R_j + (vbias - vb)/Rbias = IB(vb)。
    Newton 一维。"""
    Gtot = np.sum(1.0 / Rw)
    Gb = 1.0 / Rbias
    S = np.sum(x / Rw)  # Σ x_j/R_j
    def f(vb):
        # IB(vb)：由 Ebers-Moll 内层已解
        IC, _ = ic_of_vb(vb, x, Rw)
        return S - vb * (Gtot + Gb) + vbias * Gb - IC / BETA
    def dfd(vb):
        h = 1e-7
        return (f(vb + h) - f(vb - h)) / (2 * h)
    vb = min(np.mean(x) * 0.9, 0.62)
    for _ in range(60):
        fv, dv = f(vb), dfd(vb)
        step = fv / dv
        vb -= np.clip(step, -0.2, 0.2)
        if abs(step) < 1e-10:
            break
    IC, vbe = ic_of_vb(vb, x, Rw)
    return IC, vb, vbe

# ───────────────────────── A. 线性度 ─────────────────────────
print("=" * 70)
print("A. 线性度测试（W=4096, R0=40k, R_E=50Ω, 输入 0..200mV）")
rng = np.random.default_rng(0)
w_pos = np.abs(rng.normal(1.0, 0.5, W))          # 全正权重（先测单极性）
w_pos = w_pos / w_pos.max() * 4.0                # 标称到 4.0 → R 范围 R0/4..R0/0.1
Rw = R0 / w_pos
x_hi = 200e-3
vbias, Rbias = 620e-3, 1e6   # 偏置把基极拉到 ~0.62V

# 扫输入幅度：x = a * xref, xref 固定模式
xref = rng.uniform(0, x_hi, W)
for a in [0.05, 0.25, 0.5, 0.75, 1.0]:
    x = a * xref
    IC, vb, vbe = solve_node(vbias, x, Rw, Rbias)
    ideal = BETA / R0 * np.sum(w_pos * x)        # 理想小信号增益 β·Σ(w·x)/R0
    print(f"  幅度 {a*100:3.0f}%: IC={IC*1e9:10.3f} nA  "
          f"ideal={ideal*1e9:10.3f} nA  偏差={100*(IC/ideal-1):+6.2f}%  VBE={vbe*1e3:6.1f}mV")

# 增益稳定性：输入模式变化时增益（IC/Σwx）
gains = []
for trial in range(20):
    x = rng.uniform(0, x_hi, W)
    IC, vb, vbe = solve_node(vbias, x, Rw, Rbias)
    ideal = BETA / R0 * np.sum(w_pos * x)
    gains.append(IC / ideal)
print(f"  增益一致性（20 个随机模式）: 均值={np.mean(gains):.5f} 峰峰偏差="
      f"{100*(np.max(gains)-np.min(gains)):.2f}%")

# ───────────────────────── B. 噪声 → SNR/有效位 ─────────────────────────
print("=" * 70)
print("B. 噪声预算（带宽 BW=1.6MHz，对应模拟计算窗 ~0.3μs）")
BW = 1.6e6
# 电阻网络等效输入热噪声：R_eq = 1/Σ(1/R_j)
R_eq = 1.0 / np.sum(1.0 / Rw)
vn_r = np.sqrt(4 * kB * T * R_eq * BW)            # 输入端热噪声电压
# 基极散粒噪声：I_B ~ ideal 工作点
IC0, _, _ = solve_node(vbias, 0.5 * xref, Rw, Rbias)
IB0 = IC0 / BETA
in_b = np.sqrt(2 * q * max(IB0, 1e-15) * BW)      # A
# 折算到输入端：in_b / (β/R0) 等效… 更直接：输出端电流噪声
# 输出噪声电流 = β·in_b + 集电极热噪声(≈ R_C 的电流噪声，忽略二阶)
i_n_out = BETA * in_b
i_sig = IC0  # 信号摆幅取满幅 IC
SNR = (i_sig / i_n_out) ** 2
n_eff = 20 * np.log10(np.sqrt(SNR))
print(f"  R_eq={R_eq:.1f} Ω  电阻热噪声(输入端)={vn_r*1e9:.2f} nV/√Hz·√BW")
print(f"  I_B(50%幅)={IB0*1e9:.2f} nA  基极散粒噪声={in_b*1e9:.2f} nA")
print(f"  SNR={10*np.log10(SNR):.1f} dB → 有效位数 ≈ {n_eff:.1f} bit")
# 若 R_eq 更小（更多输入并联），噪声更低 → 报告标度
for Wn in [1024, 4096, 16384, 65536]:
    req = 1.0 / (Wn / R0 * 1.0)  # 平均 w=1 → 每支 R0 → R_eq=R0/Wn
    vn = np.sqrt(4 * kB * T * req * BW)
    print(f"    W={Wn:6d}: R_eq={req:6.1f}Ω  v_n(输入)={vn*1e9:7.2f}nV  "
          f"若满幅200mV/16bit=3μV → 噪声占比 {100*vn/3e-6:5.1f}%")

# ───────────────────────── C. 电阻容差 ─────────────────────────
print("=" * 70)
print("C. 电阻容差 Monte Carlo（输出误差 vs 理想 Σwx）")
rng2 = np.random.default_rng(1)
x = rng2.uniform(0, x_hi, W)
ideal = np.sum(w_pos * x)
for tol, nmc in [(0.01, 200), (0.001, 200), (0.0005, 200)]:
    errs = []
    for _ in range(nmc):
        Rw_m = Rw * (1 + rng2.uniform(-tol, tol, W))
        w_m = R0 / Rw_m
        errs.append(abs(np.sum(w_m * x) - ideal) / ideal)
    errs = np.array(errs)
    print(f"  容差 {tol*100:5.2f}%: 输出误差 mean={errs.mean()*100:.3f}% "
          f"p95={np.percentile(errs,95)*100:.3f}% max={errs.max()*100:.3f}%")

# ───────────────────────── D. 级联 β 累积 ─────────────────────────
print("=" * 70)
print("D. L 层电流级联的增益累积（每层 β=100，无逐层归一化）")
I = 1e-9  # 第一层基极电流 nA 级
for L in [1, 2, 5, 10, 20, 40, 60]:
    I_L = I * BETA ** L
    tag = "正常" if I_L < 1 else "★ 物理不可行（超过 1A 电源/线宽限制）"
    print(f"  L={L:3d}: I={I_L:.3e} A  {tag}")
print("  → 结论：必须逐层增益归一化（每层后接 ADC/电流镜复位到固定摆幅），")
print("    归一化位数即为逐层量化位数；这正是 Mythic/NorthPole 类混合架构的做法。")
