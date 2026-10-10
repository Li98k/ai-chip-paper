"""R1 核心仿真 v2：正确的偏置设计 + 鲁棒求解 + 规模/功耗/面积估算
修正 v1b 的两个问题：
  (1) 偏置支路电导远小于信号网络时压垮节点 → 用大 R_BIAS（≈1GΩ 等效电流源）
  (2) 牛顿法从 0.7V 初值出发被指数项卡住 → 改用二分法（F 单调，必然收敛）
设计点：R0=1MΩ（解决驱动电流），W=4096，R_E=100Ω，IC0=100µA
"""
import numpy as np

q = 1.602e-19; kB = 1.381e-23; T = 300.15
VT = kB*T/q
BETA = 100.0
IS = 1e-14
VCC = 0.9
R0 = 1e6
W = 4096
R_E = 100.0
R_BIAS = 1e9          # ≈电流源

def ic_of_vbe(vbe):
    return BETA/(BETA+1) * IS * (np.exp(np.clip(vbe, -0.2, 0.85)/VT) - 1.0)

def solve_vbe(vb):
    """vb = vbe + (IC/β)(1+1/β)R_E — 牛顿"""
    vbe = 0.62
    for _ in range(30):
        ic = ic_of_vbe(vbe)
        f = vbe + ic/BETA*(1+1/BETA)*R_E - vb
        df = 1.0 + ic/(BETA*VT)*(1+1/BETA)*R_E
        vbe -= f/df
        if abs(f/df) < 1e-13: break
    return vbe

class Node:
    """一个模拟神经元：W 支加权输入 + 偏置电流 + BJT 读出"""
    def __init__(self, w):
        self.w = w
        self.Rw = R0/w
        self.G = np.sum(1.0/self.Rw)
        self.Gb = 1.0/R_BIAS
    def S(self, x):  return np.sum(x/self.Rw)
    def IB(self, vb):
        return ic_of_vbe(solve_vbe(vb))/BETA
    def solve(self, x, ibias):
        S = self.S(x)
        f = lambda vb: S + ibias - vb*(self.G+self.Gb) - self.IB(vb)
        lo, hi = 0.02, 0.88
        for _ in range(80):
            mid = 0.5*(lo+hi)
            if f(lo)*f(mid) <= 0: hi = mid
            else: lo = mid
        vb = 0.5*(lo+hi)
        ic = ic_of_vbe(solve_vbe(vb))
        return ic, vb

rng = np.random.default_rng(42)
w = np.clip(rng.normal(1.0, 0.6, W), 0.1, 4.0)
node = Node(w)

# 设计偏置：均值输入 x̄=50mV 时 IC0=100µA
IC0 = 100e-6
VBE0 = VT*np.log(IC0*BETA/IS)
VB0 = VBE0 + (IC0/BETA)*(1+1/BETA)*R_E
xbar = np.full(W, 50e-3)
I_BIAS = VB0*node.G - node.S(xbar)
print(f"设计点: R0=1MΩ, W={W}, R_E={R_E}Ω, R_BIAS=1GΩ")
print(f"  G={node.G*1e6:.3f}µS  R_eq={1/node.G:.1f}Ω")
print(f"  VBE0={VBE0*1e3:.2f}mV  VB0={VB0*1e3:.2f}mV  I_BIAS={I_BIAS*1e6:.3f}µA")
print("="*72)

# ───── A. 线性度（二分法全 Ebers-Moll 精确解）─────
print("A. 线性度（精确解）：幅度扫描 0→100%")
xref = rng.uniform(0, 100e-3, W)
print(f"  {'幅度':>5} {'IC(nA)':>11} {'V_B(mV)':>9} {'VBE(mV)':>9} {'IC/IC0':>9}")
for a in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]:
    ic, vb = node.solve(a*xref, I_BIAS)
    vbe = solve_vbe(vb)
    print(f"  {a*100:4.0f}% {ic*1e9:11.1f} {vb*1e3:9.2f} {vbe*1e3:9.2f} {ic/IC0:9.3f}")

# 全随机模式的线性拟合：IC = k0 + k1·(Σwx)
xs, ICs = [], []
for _ in range(60):
    x = rng.uniform(0, 100e-3, W)
    s = np.sum(w*x)
    ic, vb = node.solve(x, I_BIAS)
    xs.append(s); ICs.append(ic)
xs, ICs = np.array(xs), np.array(ICs)
k1, k0 = np.polyfit(xs, ICs, 1)
pred = k0 + k1*xs
rel = np.abs(pred-ICs)/np.median(ICs)
print(f"  随机模式线性拟合: k1={k1:.3e} A/unit, 最大残差={rel.max()*100:.3f}%, "
      f"p99={np.percentile(rel*100,99):.3f}%")
# 增益一致性：构造两个内积严格相等、但分布不同的 x 向量，比较 IC
# （理论上 IC 只依赖 Σ w·x，与分布无关 —— 这是本方案的数学基石）
tgt = np.sum(w*xref)
# x_a = xref; x_b = 把 xref 的 20% 能量从一个分量挪到另一个（保持 Σwx 不变）
x_b = xref.copy()
i, j2 = int(np.argmax(xref)), int(np.argmin(xref))
d = 3e-3
x_b[i] -= d; x_b[j2] += d
tgt_b = np.sum(w*x_b)
x_b = x_b * (tgt/tgt_b)   # 微缩放使内积严格相等
tgt_b = np.sum(w*x_b)
ic_a,_ = node.solve(xref, I_BIAS)
ic_b,_ = node.solve(x_b, I_BIAS)
print(f"  内积严格相同时(|ΔΣwx|={abs(tgt-tgt_b):.1e}), IC 偏差 = "
      f"{abs(ic_a-ic_b)/ic_a*100:.6f}%  (≈0 → 输出只依赖内积，与分布无关)")
# 对照：内积差 1% 时 IC 差多少（灵敏度标定）
x_c = xref*1.01
ic_c,_ = node.solve(x_c, I_BIAS)
print(f"  灵敏度: Σwx +1% → IC 变化 {(ic_c/ic_a-1)*100:+.3f}%")

# ───── B. 噪声 → 有效位 ─────
print("="*72)
print("B. 噪声预算（BW=1.6MHz 计算窗）")
BW = 1.6e6
R_eq = 1.0/node.G
vn_in = np.sqrt(4*kB*T*R_eq*BW)
ic_fs,_ = node.solve(xref, I_BIAS)
ic_0,_  = node.solve(np.zeros(W), I_BIAS)
swing = ic_fs - ic_0
in_b = np.sqrt(2*q*(IC0/BETA)*BW)      # 基极散粒
i_n_thermal = vn_in*k1                  # 输入热噪声折算到输出电流
i_n_tot = np.sqrt(in_b**2 + i_n_thermal**2)
snr = (swing/2)**2/i_n_tot**2
print(f"  R_eq={R_eq:.1f}Ω  输入热噪声={vn_in*1e9:.1f}nV")
print(f"  IC 满幅摆幅={swing*1e6:.2f}µA  散粒={in_b*1e9:.1f}nA  热折算={i_n_thermal*1e9:.1f}nA")
print(f"  SNR={10*np.log10(snr):.1f}dB → 有效位≈{20*np.log10(np.sqrt(snr)):.1f}bit")
# 若加 1/f 噪声（BJT 基极，f0=1kHz，系数 Kf=1e-24 A/Hz 典型）：
f0 = 1e3; Kf = 1e-24
v1f = np.sqrt(Kf*(f0+ (2*BW) )* (1/R_E)**2)  # 粗估：1/f 电流噪声折算
print(f"  (粗估 1/f 噪声贡献 ≈ {v1f*1e9:.0f}nA 量级，需实测器件参数)")

# ───── C. 驱动电流与每神经元功耗 ─────
print("="*72)
print("C. 上游驱动与功耗")
# 上游神经元集电极需提供的电流：流入每条线的 I_j = (x_j - VB)/R_j
x = rng.uniform(0, 100e-3, W)
ic, vb = node.solve(x, I_BIAS)
I_lines = (x - vb)/node.Rw           # 可正可负（电压源吸收/提供）
print(f"  本节点吸入基极电流 IB={ic/BETA*1e6:.3f}µA")
print(f"  每支线电流 |I_j| 均值={np.mean(np.abs(I_lines))*1e9:.1f}nA  "
      f"max={np.max(np.abs(I_lines))*1e9:.1f}nA")
# 上游每个神经元驱动 N_down 条线（=下层神经元数），每条 ~50nA
N_down = 4096
I_drv = np.mean(np.abs(I_lines))*N_down
P_neuron = (I_BIAS + ic/BETA)*VCC + ic*(VCC*0.5)   # 偏置+读出+BJT
print(f"  上游每神经元驱动电流(N_down={N_down})≈{I_drv*1e6:.2f}µA")
print(f"  每模拟神经元静态功耗≈{P_neuron*1e6:.1f}µW")

# ───── D. 27B 规模估算（Qwen3-27B: 64层, hidden=4096, FFN=12288, GQA 8kv/32q heads）─────
print("="*72)
print("D. 27B 稠密模型的全模拟规模估算")
L, H, FFN = 64, 4096, 12284
n_ffn_w = L*(H*FFN*2 + H*H)      # FFN 上/下投影 + attention QKV/O
# 近似总参数 27e9：
n_params = 27e9
avg_fanin = n_params / (L*(FFN + H))   # 每个神经元平均输入数
n_neurons = n_params / avg_fanin
print(f"  总参数≈{n_params/1e9:.0f}B, 平均扇入≈{avg_fanin:.0f}, 模拟神经元数≈{n_neurons/1e6:.1f}M")
for name, per_node in [("基线(100µW/节点)", 100e-6),
                       ("激进(10µW/节点, R0=10MΩ)", 10e-6),
                       ("极限(1µW/节点)", 1e-6)]:
    P = n_neurons*per_node
    print(f"  {name}: 全片静态功耗 = {P:.0f} W")
# 面积：电阻单元
for name, area_um2 in [("离散多晶电阻 1MΩ (~200µm²)", 200.0),
                       ("RRAM 1T1R 28nm (~0.1µm²)", 0.1),
                       ("PCM 28nm (~0.05µm²)", 0.05)]:
    tot = n_params*area_um2
    cm2 = tot/1e6
    dies = cm2/5  # 5cm²=500mm² 先进芯片
    print(f"  权重存储 [{name}]: {n_params:.2e}×{area_um2}µm² = {cm2:.0f} cm² "
          f"≈ {dies:.0f} 片 500mm² 晶圆级芯片")
print("  → 关键结论：BJT+离散电阻方案只适合 ≤1B 级模型；")
print("    27B 必须用 RRAM/PCM 存阻单元做'参数即电阻'（与文献方向一致），")
print("    BJT/MOS 作读出放大器 —— 混合存内计算架构。")
