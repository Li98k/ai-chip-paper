"""R0 核心仿真 v1b：正确的小信号模型
电路（发射极退化负反馈版 —— 让 BJT 线性化的标准做法）：

      VCC
       |
      [R_C]
       |
       +---- Vout (集电极)
       |
   C --+-- B  (基极节点)
       |   |
      R_E  |  (各输入经 R_j=R0/w_j 汇入；另有偏置支路 V_BIAS/R_BIAS)
       |
      GND

物理要点（本轮论证的结论性发现）：
  1) 基极节点电流仅 ~µA，故节点电压 ≈ 各输入电压经电导加权的平均：
        V_B = [Σ_j x_j/R_j + V_BIAS/R_BIAS] / [Σ_j 1/R_j + 1/R_BIAS]
     即 ΔV_B ∝ Σ_j w_j·x_j   ← 电阻网络天然完成"加权求和"，与 BJT 无关！
  2) BJT 本身是指数器件 i_c=I_S·exp(V_BE/V_T)，直接放大 100mV 摆幅会严重非线性。
     必须加 R_E 发射极负反馈：此时 I_C ≈ (V_B−V_BE)/R_E，增益≈1/R_E，
     线性区大幅扩展（V_BE 只需在偏置点 ±15mV 内，I_C 变化 <30%）。
  3) 真正决定精度的是：负反馈线性度 + 噪声 + 电阻容差，而不是 β。
本脚本用 Ebers-Moll 逐点精确求解（非小信号近似），量化这三项。
"""
import numpy as np

q = 1.602e-19
kB = 1.381e-23
T = 300.15
VT = kB * T / q            # 25.86 mV
BETA = 100.0
IS = 1e-14
VA = 100.0                 # Early 电压
VCC = 1.0
R0 = 40e3
W = 4096
R_E = 100.0                # 发射极退化电阻（关键）
R_C = 1e3

def ic_emitter(vb, x, Rw, vbias, rbias):
    """Ebers-Moll 精确解：给定基极节点目标电压关系，求自洽的 (VBE, IC)。
    节点 KCL: Σ_j (x_j - VB)/R_j + (vbias - VB)/rbias = IB = IC/β·(1+VCE/VA修正)
    其中 VB = VBE + IC*(1+1/β)*R_E  (发射极电阻压降)
    未知数 VB。用牛顿法。"""
    G = np.sum(1.0/Rw); Gb = 1.0/rbias
    S = np.sum(x/Rw)                      # Σ x_j/R_j
    def F(VB):
        VBE = solve_vbe(VB)
        IC = ic_of_vbe(VBE)
        IB = IC / BETA
        return S + vbias*Gb - VB*(G+Gb) - IB
    # 牛顿
    VB = 0.70
    for _ in range(80):
        h = 1e-8
        dF = (F(VB+h)-F(VB-h))/(2*h)
        step = F(VB)/dF
        VB -= np.clip(step, -0.3, 0.3)
        if abs(step) < 1e-12: break
    VBE = solve_vbe(VB)
    IC = ic_of_vbe(VBE)
    return IC, VB, VBE

def solve_vbe(VB, R_E=R_E):
    """解 VBE: VB = VBE + (IC(VBE)/β)(1+1/β) R_E — 牛顿法，~5 次收敛"""
    VBE = 0.60
    for _ in range(50):
        IC = ic_of_vbe(VBE)
        f = VBE + IC/BETA*(1+1/BETA)*R_E - VB
        df = 1.0 + (IC/(BETA*VT))*(1+1/BETA)*R_E
        step = f/df
        VBE -= step
        if abs(step) < 1e-13:
            break
    return VBE

def ic_of_vbe(VBE):
    VBE = np.clip(VBE, -0.3, 0.9)
    IC0 = BETA/(BETA+1) * IS * (np.exp(VBE/VT) - 1.0)
    return IC0   # Early 效应在 VCE~0.5V 时修正 <1%，忽略

# ── 设计偏置点：x 全取均值时 I_C0 = 100µA ──
rng = np.random.default_rng(0)
w = np.abs(rng.normal(1.0, 0.5, W)); w = 4.0*w/w.max()
Rw = R0/w
G = np.sum(1.0/Rw)
x_full = rng.uniform(0, 100e-3, W)
x_mean = x_full.mean()
# 目标：VBE0 使 IC0=100µA
IC0_target = 100e-6
VBE0 = VT*np.log(IC0_target*BETA/IS)
# 反推所需 VB0 = VBE0 + (IC0/β)(1+1/β)R_E
VB0 = VBE0 + (IC0_target/BETA)*(1+1/BETA)*R_E
# 偏置支路提供：在 x 均值下 VB=VB0。用一个大 R_BIAS + V_BIAS 注入
# 设 R_BIAS = G*R0 (即与信号网络同量级)，解 V_BIAS：
R_BIAS = R0*G            # = R0/平均w → 每支平均电导
V_BIAS = (VB0*(G+1.0/R_BIAS) - x_mean*np.sum(1.0/Rw)) * R_BIAS
print(f"设计点: W={W}, R0={R0/1e3}kΩ, R_E={R_E}Ω, IC0=100µA, VBE0={VBE0*1e3:.1f}mV")
print(f"  V_BIAS={V_BIAS*1e3:.1f}mV, R_BIAS={R_BIAS/1e3:.1f}kΩ")
print("=" * 72)

# ───────────── A. 线性度（Ebers-Moll 精确，非小信号）─────────────
print("A. 线性度：全 Ebers-Moll 精确解，输入 0→100mV 摆幅")
xref = rng.uniform(0, 100e-3, W)
# 理想参考：节点电压理想值 V_B_id = [Σ x/R + V_BIAS/R_BIAS]/(G+1/R_BIAS)
def vB_ideal(x):
    return (np.sum(x/Rw) + V_BIAS/R_BIAS)/(G + 1.0/R_BIAS)
print(f"  {'幅度':>5} {'IC(nA)':>12} {'V_B(mV)':>9} {'VBE(mV)':>9} {'相对IC0':>10}")
for a in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
    x = a*xref
    IC, VB, VBE = ic_emitter(VB0, x, Rw, V_BIAS, R_BIAS)
    vB_id = vB_ideal(x)
    ratio = IC/IC0_target
    print(f"  {a*100:4.0f}% {IC*1e9:12.1f} {VB*1e3:9.2f} {VBE*1e3:9.2f} {ratio:10.3f}")

# 线性度量化：拟合 IC vs Σwx，看最大偏离
xs = []
ICs = []
for _ in range(30):
    x = rng.uniform(0, 100e-3, W)
    s = np.sum(w*x)
    IC, VB, VBE = ic_emitter(VB0, x, Rw, V_BIAS, R_BIAS)
    xs.append(s); ICs.append(IC)
xs = np.array(xs); ICs = np.array(ICs)
# 线性拟合 IC = k0 + k1*s
k1, k0 = np.polyfit(xs, ICs, 1)
pred = k0 + k1*xs
maxdev = np.max(np.abs(pred-ICs))/np.median(ICs)
print(f"  线性拟合残差(最大/中值) = {maxdev*100:.2f}%   (越低越线性)")
print(f"  小信号增益 k1 = {k1:.4e} A/(V·W-unit)")

# ───────────── B. 噪声 → 有效位 ─────────────
print("=" * 72)
print("B. 噪声 → SNR / 有效位数（BW=1.6MHz）")
BW = 1.6e6
R_eq = 1.0/G                      # 信号网络等效电阻
vn_in = np.sqrt(4*kB*T*R_eq*BW)   # 输入端热噪声
# 输出端：I_C 的散粒噪声 + 输入折算
i_n_out = BETA * np.sqrt(2*q*(IC0_target/BETA)*BW)   # 基极散粒折算
# 热噪声折算到 IC：vn_in / (V→IC 的 transresistance = 1/k1)
i_n_thermal = vn_in * k1
i_n_tot = np.sqrt(i_n_out**2 + i_n_thermal**2)
# 信号摆幅：满幅时 IC 变化
IC_hi, _, _ = ic_emitter(VB0, xref, Rw, V_BIAS, R_BIAS)
IC_lo, _, _ = ic_emitter(VB0, np.zeros(W), Rw, V_BIAS, R_BIAS)
swing = IC_hi - IC_lo
SNR = (swing/2)**2 / i_n_tot**2   # 半幅信号
n_eff = 20*np.log10(np.sqrt(SNR))
print(f"  R_eq={R_eq:.2f}Ω  输入热噪声={vn_in*1e9:.1f}nV")
print(f"  IC摆幅(0→满)={swing*1e9:.1f}nA  总噪声={i_n_tot*1e9:.2f}nA")
print(f"  SNR={10*np.log10(SNR):.1f}dB → 有效位≈{n_eff:.1f}bit")

# ───────────── C. 电阻容差 ─────────────
print("=" * 72)
print("C. 电阻容差 Monte Carlo（对 Σwx 的误差）")
x = rng.uniform(0, 100e-3, W)
ideal = np.sum(w*x)
for tol in [0.01, 0.001, 0.0005]:
    errs = []
    for _ in range(300):
        Rw_m = Rw*(1+rng.uniform(-tol, tol, W))
        errs.append(abs(np.sum((R0/Rw_m)*x) - ideal)/ideal)
    errs = np.array(errs)
    print(f"  容差{tol*100:5.2f}%: mean={errs.mean()*100:.3f}% p95={np.percentile(errs,95)*100:.3f}%")

# ───────────── D. 级联 ─────────────
print("=" * 72)
print("D. 层间增益累积与归一化（每层后接 ADC 复位到固定摆幅）")
print("  无归一化时 I_L = I_1·β^L：")
I = 100e-6
for L in [1,2,3,4,5]:
    print(f"    L={L}: {I*BETA**L:.3e} A {'OK' if I*BETA**L<1 else '★不可行'}")
print("  → 结论：每层输出必须经 8~16bit ADC/电流镜归一化回固定电平整幅，")
print("    归一化位数=逐层量化位数（这正是模拟 CIM 芯片的标准做法）。")
