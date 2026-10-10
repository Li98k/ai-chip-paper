"""R1 核心仿真 v3：朴素基极拓扑的非线性刻画 + 发射极负反馈线性化的定量解
核心问题：把 Σ(x_j/R_j) 的电阻分压节点直接接 BJT 基极，
IC = α·IS·exp(V_BE/VT) 是指数 → 全量程非线性。
v3 定量回答：
  Q1. 不加 R_E：非线性有多严重？（幅度扫描 + 全量程谐波）
  Q2. 加 R_E：多大 R_E 才达到 INT8/INT16 全局线性？代价（压降/带宽/面积）？
  Q3. 正确的"电流模 KCL 求和 + 反馈读出"架构下，线性度与精度上限？
  Q4. 与 RRAM/PCM 存阻单元方案对比（面积/精度/可写性）
"""
import numpy as np
q=1.602e-19; kB=1.381e-23; T=300.15; VT=kB*T/q
BETA=100.0; IS=1e-14
R0=1e6; W=4096; VCC=1.8
def ic_of_vbe(v): return BETA/(BETA+1)*IS*(np.exp(np.clip(v,-0.2,0.9)/VT)-1.0)

def make_node(w, R_E):
    Rw=R0/w; G=np.sum(1.0/Rw); Gb=0.0
    def solve(x, ibias):
        S=np.sum(x/Rw)
        def F(vb):
            # VBE = vb - (IC/β)(1+1/β)R_E
            vbe=0.65
            for _ in range(40):
                ic=ic_of_vbe(vbe)
                vbe_new=vb-ic/BETA*(1+1/BETA)*R_E
                if abs(vbe_new-vbe)<1e-13: break
                vbe=0.5*(vbe+vbe_new)
            ib=ic_of_vbe(vbe)/BETA
            return S+ibias-vb*G-ib
        lo,hi=0.02,0.9
        for _ in range(70):
            mid=0.5*(lo+hi)
            if F(lo)*F(mid)<=0: hi=mid
            else: lo=mid
        vb=0.5*(lo+hi)
        vbe=vb
        for _ in range(40):
            vbe_new=vb-ic_of_vbe(vbe)/BETA*(1+1/BETA)*R_E
            if abs(vbe_new-vbe)<1e-13: break
            vbe=0.5*(vbe+vbe_new)
        return ic_of_vbe(vbe),vb,vbe
    return solve

rng=np.random.default_rng(7)
w=np.clip(rng.normal(1.0,0.6,W),0.1,4.0)
xref=rng.uniform(0,100e-3,W)
IC0=100e-6
VBE0=VT*np.log(IC0*BETA/IS)

print("="*72)
print("Q1/Q2. R_E 扫描：全量程(0→100%)非线性 vs 压降代价")
print(f"  VBE0={VBE0*1e3:.1f}mV (IC0=100µA)")
print(f"  {'R_E':>7} {'VB0(mV)':>8} {'0%IC':>8} {'100%IC':>8} {'线性偏差%':>9} "
      f"{'IC摆幅':>8} {'IE·R_E压降':>10} {'VCC够?':>6} {'gm·R_E':>7}")
results={}
for R_E in [0, 26, 52, 100, 200, 500, 1000, 2000]:
    solve=make_node(w,R_E)
    # 设计偏置：x̄=50mV 时 IC=IC0
    # VB0 = VBE0 + (IC0/β)(1+1/β)R_E
    VB0=VBE0+(IC0/BETA)*(1+1/BETA)*R_E
    G=np.sum(1.0/(R0/w))
    # ibias 使 vb=VB0 at x=xbar
    xbar=np.full(W,50e-3)
    # solve 需要 ibias；反推：F(VB0)=0 → ibias = VB0*G - Σx/R + ib(VB0)
    # 近似 ib≈IC0/β
    ibias=VB0*G-np.sum(xbar/(R0/w))+IC0/BETA
    ICa,vba,vbea=solve(0*xref,ibias)
    ICb,vbb,vbeb=solve(1*xref,ibias)
    # 线性偏差：中点 vs 端点中值
    ICm,vbm,vbem=solve(0.5*xref,ibias)
    linear_mid=0.5*(ICa+ICb)
    dev=abs(ICm-linear_mid)/ICb*100
    swing=ICb-ICa
    drop=(IC0/BETA)*(1+1/BETA)*R_E* (ICb/IC0)  # 满幅发射极压降(近似用中点)
    drop_mid=(ICm/BETA)*(1+1/BETA)*R_E
    gm=IC0/VT
    ok = "是" if (VB0+drop_mid)<VCC-0.2 else "否★"
    results[R_E]=(dev,swing,drop_mid,gm*R_E)
    print(f"  {R_E:6.0f}Ω {VB0*1e3:8.1f} {ICa*1e6:8.2f} {ICb*1e6:8.2f} {dev:9.3f} "
          f"{swing*1e6:8.2f} {drop_mid*1e3:9.1f}mV {ok:>5} {gm*R_E:7.1f}")

print()
print("  解读：线性偏差<0.4%(INT8 需 ±1/256≈0.4%) 的最小 R_E 即设计下限；")
print("        gm·R_E>>1 是负反馈线性化的小信号条件；IE·R_E 压降吃电源。")

# 选一个满足 INT8 的 R_E，做全细节
R_E=500.0
solve=make_node(w,R_E)
VB0=VBE0+(IC0/BETA)*(1+1/BETA)*R_E
G=np.sum(1.0/(R0/w)); xbar=np.full(W,50e-3)
ibias=VB0*G-np.sum(xbar/(R0/w))+IC0/BETA
print("="*72)
print(f"Q3. 选定 R_E={R_E}Ω 的全细节（INT8 目标）")
# 幅度扫描
print("  幅度扫描(精确 Ebers-Moll):")
print(f"    {'amp':>4} {'IC(µA)':>9} {'V_B(mV)':>9} {'VBE(mV)':>9}")
sweep=[]
for a in np.linspace(0,1,11):
    ic,vb,vbe=solve(a*xref,ibias)
    sweep.append((a,ic,vb,vbe))
    print(f"    {a*100:3.0f}% {ic*1e6:9.3f} {vb*1e3:9.2f} {vbe*1e3:9.2f}")
# 线性拟合全量程
xs=[np.sum(w*(a*xref)) for a,_,_,_ in sweep]
ics=[ic for _,ic,_,_ in sweep]
xs=np.array(xs); ics=np.array(ics)
k1,k0=np.polyfit(xs,ics,1)
resid=np.abs(k0+k1*xs-ics)/ics
print(f"  全量程线性拟合: 最大残差={resid.max()*100:.3f}%  p99={np.percentile(resid*100,99):.3f}%")
print(f"  → INT8(需0.39%): {'达标' if resid.max()<0.0039 else '不达标'}  "
      f"INT16(需0.008%): {'达标' if resid.max()<0.00008 else '不达标'}")

# 噪声（R_E=500 版）
BW=1.6e6; R_eq=1.0/G
vn=np.sqrt(4*kB*T*R_eq*BW)
ic_fs,_,_=solve(xref,ibias); ic_0,_,_=solve(0*xref,ibias)
swing=ic_fs-ic_0
inb=np.sqrt(2*q*(IC0/BETA)*BW)
i_th=vn*k1
i_tot=np.sqrt(inb**2+i_th**2)
snr=(swing/2)**2/i_tot**2
print(f"  噪声: R_eq={R_eq:.0f}Ω v_n={vn*1e9:.0f}nV 散粒={inb*1e9:.1f}nA 热折算={i_th*1e9:.1f}nA")
print(f"        摆幅={swing*1e6:.2f}µA SNR={10*np.log10(snr):.1f}dB 有效位≈{20*np.log10(np.sqrt(snr)):.1f}bit")

# 每节点功耗 & 上游驱动
x=xref; ic,vb,vbe=solve(x,ibias)
I_lines=(x-vb)/(R0/w)
N_down=4096
P_node=(ibias+ic/BETA)*VCC+ic*(0.4*VCC)
print(f"  上游每支线 |I_j| 均值={np.mean(np.abs(I_lines))*1e9:.0f}nA "
      f"max={np.max(np.abs(I_lines))*1e9:.0f}nA")
print(f"  上游每神经元驱动(N_down={N_down})={np.mean(np.abs(I_lines))*N_down*1e6:.2f}µA")
print(f"  每模拟节点静态功耗≈{P_node*1e6:.0f}µW")

# 27B 规模（复用结论，给出 R_E=500 版功耗）
L,H,FFN=64,4096,12284
n_params=27e9; avg_fanin=n_params/(L*(FFN+H)); n_neurons=n_params/avg_fanin
print("="*72)
print("Q4. 规模结论 (27B 稠密, 平均扇入≈%.0f, 模拟神经元≈%.2fM)"%(avg_fanin,n_neurons/1e6))
print(f"  BJT+多晶电阻(200µm²/参数): {n_params*200/1e6:.0f} cm² ≈ {n_params*200/1e6/5:.0f} 片 500mm²")
print(f"  BJT+RRAM 1T1R(0.1µm²/参数):  {n_params*0.1/1e6:.0f} cm² ≈ {n_params*0.1/1e6/5:.0f} 片 500mm²")
Pchip=n_neurons*P_node
print(f"  全片静态功耗(R_E={R_E}Ω 版, 每节点{P_node*1e6:.0f}µW) = {Pchip:.0f} W")
print("  → 27B 全模拟 = 数百瓦级 + 数百 cm² → 不现实；")
print("    现实落点：① ≤1B 端侧全模拟；② 27B 用 RRAM 存阻 + 数字/模拟混合(FFN 模拟, attention 数字)。")
