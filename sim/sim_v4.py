"""R1 核心仿真 v4（物理自洽版）
电路（用户方案的形式化）：
    上层 j=1..W 个神经元输出电压 x_j (≈0~100mV)
    各经电阻 R_j = R0/w_j 接到 BJT 基极节点 VB
    基极节点另接一个高阻偏置电流源 I_bias
    BJT 发射极串 R_E 到地，集电极接 VCC（经小负载），输出 I_C

KCL（基极节点）：
    Σ_j (x_j - VB)/R_j  + I_bias  = I_B  = I_C/β
    ⇒  Σ_j x_j/R_j  =  VB·G + I_C/β ,  G=Σ 1/R_j
    加权求和 Σ x_j/R_j 被拆成两部分：节点电位泄漏 VB·G + 晶体管基极电流。
    输出 I_C = f(Σ x_j/R_j)，但 f 含 VB(→I_C) 的自洽非线性 ← 核心矛盾。

关键物理量（本模块定量）：
  (a) 工作点与线性度（幅度/模式扫描，Ebers-Moll 全模型）
  (b) 共模失配直流：x̄ 与 VB 的差 × G = 每节点直流电流 → 功耗（可行性要害）
  (c) R0(G) 的三难：↑R0 → ↓直流功耗、↑RC延迟、↑热噪声
  (d) 规模/面积/功耗地图（离散电阻 vs RRAM）
"""
import numpy as np
q=1.602e-19; kB=1.381e-23; T=300.15; VT=kB*T/q
BETA=100.0; VCC=1.8
IS=1e-14            # 集电极饱和电流（I_C=IS·e^{VBE/VT}）
def ic_of_vbe(v): return IS*np.exp(np.clip(v,-0.2,0.92)/VT)

class Node:
    """一个模拟神经元：W 支 R_j 加权输入 + 偏置电流 + BJT 读出"""
    def __init__(self, w, R0, R_E):
        self.w=w; self.R0=R0; self.R_E=R_E
        self.Rw=R0/w
        self.G=np.sum(1.0/self.Rw)
    def _vbe(self, vb):
        # vb = vbe + I_C(vbe)(1+1/β)R_E  —— 牛顿（含反馈，修正 BUG-1）
        vbe=0.6
        for _ in range(60):
            ic=ic_of_vbe(vbe)
            f=vbe+ic*(1+1.0/BETA)*self.R_E-vb
            df=1.0+ic/VT*(1+1.0/BETA)*self.R_E
            s=f/df; vbe-=s
            if abs(s)<1e-14: break
        return vbe
    def solve(self, x, ibias):
        S=np.sum(x/self.Rw); G=self.G
        def F(vb): return S+ibias-vb*G-ic_of_vbe(self._vbe(vb))/BETA
        lo,hi=1e-3, VCC-0.05            # 修正 BUG：区间覆盖 VB0（可>1V）
        for _ in range(100):
            mid=0.5*(lo+hi)
            if F(lo)*F(mid)<=0: hi=mid
            else: lo=mid
        vb=0.5*(lo+hi); vbe=self._vbe(vb); ic=ic_of_vbe(vbe)
        return ic,vb,vbe
    def design(self, xbar, IC0):
        """给定输入均值 xbar 与目标 I_C0，求 VBE0/VB0/I_bias"""
        VBE0=VT*np.log(IC0/IS)
        VB0=VBE0+IC0*(1+1.0/BETA)*self.R_E
        ibias=(VB0-xbar)*self.G+IC0/BETA     # 由 KCL 反推
        return VBE0,VB0,ibias

rng=np.random.default_rng(7)
w=np.clip(rng.normal(1.0,0.6,4096),0.1,4.0)

# ── S1 工作点校验 ──
print("S1. 工作点自洽校验")
for R_E,IC0 in [(260.0,200e-6),(1000.0,1e-3),(2600.0,200e-6)]:
    node=Node(w,1e6,R_E)
    VBE0,VB0,ibias=node.design(50e-3,IC0)
    ic,vb,vbe=node.solve(np.full(4096,50e-3),ibias)
    print(f"  R_E={R_E:5.0f}Ω IC0={IC0*1e6:4.0f}µA: 设计VB0={VB0*1e3:6.1f}mV "
          f"→ 数值VB={vb*1e3:6.1f}mV IC={ic*1e6:7.2f}µA (偏差{abs(ic/IC0-1)*100:.2f}%)")
    assert abs(ic/IC0-1)<0.005, "工作点不自洽!"
print("  ✓ 全部自洽（<0.5%）")

# ── S2 线性度 + 共模失配直流/功耗（核心）──
print("="*78)
print("S2. 线性度 与 共模失配直流功耗（W=4096, R0=1MΩ, x~U(0,100mV)）")
xref=rng.uniform(0,100e-3,4096)
print(f"  {'R_E':>6} {'IC0':>7} {'VB0':>7} {'Ibias':>8} {'非线性%':>8} {'I_dc共模':>9} "
      f"{'P_节点':>8} {'V_E满幅':>7} {'头空间':>6}")
for R_E in [260.0,1000.0,2600.0]:
    for IC0 in [200e-6,1e-3]:
        node=Node(w,1e6,R_E)
        VBE0,VB0,ibias=node.design(50e-3,IC0)
        # 幅度扫描非线性（0→满幅，15点，对 VB 线性拟合残差/摆幅）
        pts=[node.solve(a*xref,ibias) for a in np.linspace(0,1,15)]
        vbs=np.array([p[1] for p in pts]); ics=np.array([p[0] for p in pts])
        if ics.max()-ics.min()<1e-15: nl=0.0
        else:
            k1,k0=np.polyfit(vbs,ics,1)
            nl=np.max(np.abs(k0+k1*vbs-ics))/(ics.max()-ics.min())*100
        # 共模失配直流：所有输入=均值时，电阻网络抽走的电流 (VB0-x̄)·G
        I_dc=(VB0-50e-3)*node.G
        # 节点静态功耗：偏置电流源提供 I_bias（含共模），BJT 集电极取 VCC-VE
        P_node=ibias*VCC+IC0*(VCC-VBE0-IC0*(1+1/BETA)*R_E)
        VE_full=IC0*(1+1/BETA)*R_E*(ics.max()/IC0)   # 满幅发射极压降
        head=VCC-(VBE0+VE_full)
        print(f"  {R_E:5.0f}Ω {IC0*1e6:6.0f}µA {VB0*1e3:6.1f}m {ibias*1e6:7.1f}µA "
              f"{nl:8.3f} {I_dc*1e6:8.1f}µA {P_node*1e6:7.1f}µW {VE_full*1e3:6.1f}mV "
              f"{'✓' if head>0.15 else '✗':>5}")
print("  解读: I_dc共模=(VB0-x̄)·G 是每节点必须持续的直流（与信号无关）；")
print("        它随 VB0(≈VBE0+IC0·R_E) 和 G(=Σ1/R_j) 线性增长 —— 可行性第一杀手。")

# ── S3 R0 三难（固定 R_E=1kΩ, IC0=1mA）──
print("="*78)
print("S3. R0(G) 三难：直流功耗 vs 热噪声 vs RC延迟 (R_E=1kΩ,IC0=1mA,W=4096)")
nodeE=Node(w,1e6,1000.0)
print(f"  {'R0':>8} {'G(µS)':>8} {'I_dc共模':>9} {'P_节点':>8} {'v_n(1.6MHz)':>11} "
      f"{'RC延迟(ns)':>10} {'每支线I_dc':>10}")
for R0 in [100e3,300e3,1e6,3e6,10e6,30e6]:
    node=Node(w,R0,1000.0)
    VBE0,VB0,ibias=node.design(50e-3,1e-3)
    I_dc=(VB0-50e-3)*node.G
    P_node=ibias*VCC+1e-3*(VCC-VBE0-1e-3*1.01*1000)
    BW=1.6e6; R_eq=1.0/node.G
    vn=np.sqrt(4*kB*T*R_eq*BW)
    # RC延迟：节点等效电阻 R_eq 对节点电容 C_n (取 5fF 寄生) 的 tau
    C_n=5e-15; tau=R_eq*C_n
    I_line_dc=(VB0-50e-3)/node.Rw   # 每支线
    print(f"  {R0/1e3:6.0f}k {node.G*1e6:8.2f} {I_dc*1e6:8.1f}µA {P_node*1e6:7.1f}µW "
          f"{vn*1e9:10.1f}nV {tau*1e9:9.1f}n {np.mean(np.abs(I_line_dc))*1e9:9.1f}nA")
print("  解读: R0↑ → 直流/每支线电流↓（好），但 v_n↑、tau↑（坏）。")
print("        最优点受'计算窗口'(tau≪T_compute) 与 'P_budget' 共同约束。")

# ── S4 规模/面积/功耗地图 ──
print("="*78)
print("S4. 规模地图（每节点取 R_E=1k,IC0=1mA 角点功耗；面积按参数数）")
# 用 S3 中 R0=1MΩ 的 P_node
node=Node(w,1e6,1000.0); _,VB0,ibias=node.design(50e-3,1e-3)
P_node=ibias*VCC+1e-3*(VCC-0.655-1.01)
def cm2(um2): return um2/1e8
print(f"  单节点静态功耗≈{P_node*1e6:.0f}µW (R0=1MΩ 角点)")
print(f"  {'参数':>8} {'神经元数':>9} {'全片功耗':>9} | {'离散200µm²/cm²':>14} {'RRAM0.1µm²/cm²':>14}")
for n,fan in [(1e7,4096),(1e8,4096),(1e9,4096),(27e9,25000)]:
    n_neur=n/fan
    P=n_neur*P_node
    a_disc=cm2(n*200.0); a_rram=cm2(n*0.1)
    print(f"  {n/1e6:7.0f}M {n_neur/1e3:8.0f}k {P:8.1f}W | {a_disc:13.1f}cm² {a_rram:13.2f}cm²")
print("  → 1B 参数离散电阻≈20000cm²(4000片) 不现实；RRAM≈2700cm² 仍大但可多片；")
print("    ≤10M~100M 参数端侧全模拟(BJT+片上电阻) 才现实。")
print("  → 27B 必须: RRAM 存阻做权重 + 数字/混合读出差分放大(虚拟地求和, 无共模失配)。")
