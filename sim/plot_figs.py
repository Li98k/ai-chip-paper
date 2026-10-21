"""生成论文关键图（4 幅）"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams["font.family"]="sans-serif"
rcParams["font.sans-serif"]=["Noto Sans CJK SC","Noto Sans CJK JP","Droid Sans Fallback","WenQuanYi Zen Hei","SimHei","DejaVu Sans"]
rcParams["axes.unicode_minus"]=False
OUT="/home/chiva/AI_video/AI_chip_paper/sim/figs"
import os; os.makedirs(OUT, exist_ok=True)

q=1.602e-19; kB=1.381e-23; T=300.15; VT=kB*T/q
BETA=100.0; IS=1e-14; R0=1e6; W=4096
def ic_of_vbe(v): return IS*np.exp(np.clip(v,-0.2,0.92)/VT)
rng=np.random.default_rng(7)
w=np.clip(rng.normal(1.0,0.6,W),0.1,4.0)
Rw=R0/w; G=np.sum(1.0/Rw)

class Node:
    def __init__(s, R_E): s.R_E=R_E
    def _vbe(s, vb):
        vbe=0.6
        for _ in range(60):
            ic=ic_of_vbe(vbe)
            f=vbe+ic*(1+1/BETA)*s.R_E-vb
            df=1+ic/VT*(1+1/BETA)*s.R_E
            vbe-=f/df
            if abs(f/df)<1e-14: break
        return vbe
    def solve(s, x, ibias):
        S=np.sum(x/Rw)
        F=lambda vb: S+ibias-vb*G-ic_of_vbe(s._vbe(vb))/BETA
        lo,hi=1e-3,1.75
        for _ in range(100):
            mid=0.5*(lo+hi)
            if F(lo)*F(mid)<=0: hi=mid
            else: lo=mid
        vb=0.5*(lo+hi); vbe=s._vbe(vb)
        return ic_of_vbe(vbe),vb,vbe
    def design(s, xbar, IC0):
        VBE0=VT*np.log(IC0/IS); VB0=VBE0+IC0*(1+1/BETA)*s.R_E
        return VBE0,VB0,(VB0-xbar)*G+IC0/BETA

xref=rng.uniform(0,100e-3,W)

# ── 图1: 电压模朴素拓扑的指数非线性 vs 负反馈线性化 ──
fig,ax=plt.subplots(1,2,figsize=(11,4.2))
for R_E,c in [(0,"tab:red"),(260,"tab:orange"),(2600,"tab:blue")]:
    n=Node(R_E); IC0=200e-6
    _,VB0,ibias=n.design(50e-3,IC0)
    amps=np.linspace(0,1,41)
    ics=[]; vbs=[]
    for a in amps:
        ic,vb,vbe=n.solve(a*xref,ibias)
        ics.append(ic); vbs.append(vb)
    ics=np.array(ics); vbs=np.array(vbs)
    if R_E==0:
        # R_E=0 时 IC 指数爆炸，截断显示
        ics=np.clip(ics,0,IC0*30)
        ax[0].plot(amps*100,ics/IC0*100,"-",color=c,lw=2,
                   label=f"R_E=0 (IC clip @30x, 指数爆炸)")
    else:
        ax[0].plot(vbs,vbs/1e3*0+ics/IC0*100,"-",color=c,lw=2,
                   label=f"R_E={R_E:.0f}Ω (V_B→I_C 曲线)")
        # 同时以 V_B 为横轴
ax[0].set_xlabel("输入幅度 (%)  [R_E=0] / 无"); ax[0].set_ylabel("I_C / I_C0 (%)")
# 重画图1：左图 R_E=0 对幅度，右图 R_E>0 对 V_B
fig.clear()
ax=plt.subplots(1,2,figsize=(11,4.2))[1]
n0=Node(0); _,VB0,ibias=n0.design(50e-3,200e-6)
amps=np.linspace(0,1,41); ics0=[min(n0.solve(a*xref,ibias)[0],200e-6*30) for a in amps]
ax[0].plot(amps*100,np.array(ics0)/200e-6*100,"-",color="tab:red",lw=2)
ax[0].axhline(100,ls=":",c="gray")
ax[0].set_title("No R_E: exponential blowup\n(IC saturates at 30x within ~30% amp)")
ax[0].set_xlabel("input amplitude (%)"); ax[0].set_ylabel("I_C/I_C0 (%)")
n1=Node(2600); _,VB0,ibias=n1.design(50e-3,200e-6)
vbs=[];ics1=[]
for a in np.linspace(0,1,41):
    ic,vb,vbe=n1.solve(a*xref,ibias); vbs.append(vb); ics1.append(ic)
ax[1].plot(np.array(vbs)*1e3,np.array(ics1)/200e-6*100,"-",color="tab:blue",lw=2,
           label="R_E=2.6kΩ")
n2=Node(260); _,VB0,ibias=n2.design(50e-3,1000e-6)
vbs2=[];ics2=[]
for a in np.linspace(0,1,41):
    ic,vb,vbe=n2.solve(a*xref,ibias); vbs2.append(vb); ics2.append(ic)
ax[1].plot(np.array(vbs2)*1e3,np.array(ics2)/1000e-6*100,"--",color="tab:orange",lw=2,
           label="R_E=260Ω (I_C0=1mA)")
ax[1].set_title("With R_E: emitter degeneration linearizes")
ax[1].set_xlabel("V_B (mV)"); ax[1].set_ylabel("I_C/I_C0 (%)"); ax[1].legend()
plt.tight_layout(); plt.savefig(f"{OUT}/fig1_voltage_mode.pdf"); plt.savefig(f"{OUT}/fig1_voltage_mode.png",dpi=140)
print("fig1 done")

# ── 图2: 电流模虚拟地架构 —— 线性求和 + 噪声 ──
w2=np.clip(rng.normal(0,1.0,W),-4,4)
wp=np.clip(w2,0,None); wn=np.clip(-w2,0,None)
Gp_arr=wp/R0; Gn_arr=wn/R0           # 逐支路电导(避免 R0/0 除零; 语义与原 R0/w 完全一致)
Gp=np.sum(Gp_arr); Gn=np.sum(Gn_arr)
def imac(x,G): return np.sum(x*G)
x=rng.uniform(0,1.0,W)
a_scan=np.linspace(0.02,1,40)
sig=[];snr=[]
Req=1/(Gp+Gn); BW=1.6e6
vn=np.sqrt(4*kB*T*Req*BW)
for a in a_scan:
    ip=imac(a*x,Gp_arr); ino=imac(a*x,Gn_arr)
    ia=abs(ip-ino)
    ish=np.sqrt(2*q*ia*BW)
    it=np.sqrt((vn*(Gp+Gn))**2+ish**2)
    sig.append(ia); snr.append(20*np.log10(ia/it))
fig,ax=plt.subplots(1,2,figsize=(11,4.2))
ax[0].plot(a_scan,np.array(sig)*1e9,"-",lw=2,color="tab:blue")
ax[0].plot([0,1],[0,abs(imac(x,Gp_arr)-imac(x,Gn_arr))*1e9],"--",c="gray",lw=1,
           label="ideal slope = (I_p-I_n)")
ax[0].set_xlabel("input scale a (x = a·x_ref)"); ax[0].set_ylabel("|I_out| (nA)")
ax[0].set_title("Current-mode virtual-ground summation\n(linear, no DC backflow)")
ax[0].legend()
ax[1].plot(a_scan,snr,"-",lw=2,color="tab:green")
ax[1].axhline(42,ls=":",c="red"); ax[1].axhline(60,ls=":",c="orange")
ax[1].text(0.5,43,"42 dB (ENOB 8bit)",color="red",fontsize=9)
ax[1].text(0.5,61,"60 dB (ENOB 12bit)",color="orange",fontsize=9)
ax[1].set_xlabel("input scale a"); ax[1].set_ylabel("SNR (dB)")
ax[1].set_title("Noise floor: thermal + shot (BW=1.6MHz)")
plt.tight_layout(); plt.savefig(f"{OUT}/fig2_current_mode.pdf"); plt.savefig(f"{OUT}/fig2_current_mode.png",dpi=140)
print("fig2 done")

# ── 图3: 真实约束三难（v9 修正版）：面积 vs 噪声/吞吐 vs 容差 ──
# 面板A: 参数量 vs 所需硅面积（不同工艺节点）—— 硬约束1
ns=np.logspace(3,10.6,300)  # 1e3 .. 4e10 参数
fig,ax=plt.subplots(1,3,figsize=(12.5,4))
for tag,ac,cl in [("45nm 4µm²",4.0,"tab:red"),("7nm 0.1µm²",0.1,"tab:orange"),("3nm 0.04µm²",0.04,"tab:green")]:
    area_cm2 = ns*ac/1e8
    ax[0].loglog(ns/1e6, area_cm2, lw=2, color=cl, label=tag)
ax[0].axhline(500,ls=":",c="gray"); ax[0].text(1.2,560,"500 cm² = 500 × 1cm² die (≈58 reticle dies)",fontsize=8)
ax[0].axhline(100,ls="--",c="gray"); ax[0].text(1.2,110,"100 cm² = 100 × 1cm² die (≈12 reticle dies)",fontsize=8)
ax[0].axvline(2.7e4,ls=":",c="k",lw=1); ax[0].text(2.8e4,2,"27B",fontsize=9)
ax[0].set_xlim(0.8,60000)
ax[0].set_xlabel("model size (M params)"); ax[0].set_ylabel("weight-array area (cm²)")
ax[0].set_title("Hard limit 1: 1 param = 1 memory cell\narea ∝ param count"); ax[0].legend(fontsize=8)
# 面板B: 随机输入 SNR vs 吞吐（R7 修正公式: E[x²]=V²/3, E[Σ|w|]=W·0.7979）
# std 基: SNR = 0.0577/√(3.1916·kT·BW·R0)；MC 中位数低 3.4dB（半正态中位）
Tops=np.logspace(3,9,60)  # 1kOPS..1GOPS
BWarr=1/(2*(1/Tops))      # T_step=1/ops → BW=ops/2
R0ref=1e6
snr_r=20*np.log10(0.0577/np.sqrt(3.1916*1.381e-23*300*BWarr*R0ref))
snr_r_100k=snr_r+20*np.log10(np.sqrt(R0ref/1e5))  # R0=100kΩ 时 +10dB
ax[1].loglog(Tops/1e6, snr_r, lw=2.5, color="tab:blue", label="R0=1MΩ (std-based)")
ax[1].loglog(Tops/1e6, snr_r_100k, lw=2, ls="--", color="tab:cyan", label="R0=100kΩ (+10dB)")
ax[1].axhline(49.9,ls=":",c="red"); ax[1].text(1.1,52.5,"49.9 dB = INT8 (6.02×8+1.76)",color="red",fontsize=8)
ax[1].axhline(25.8,ls="--",c="orange"); ax[1].text(1.1,27.5,"25.8 dB = INT4",color="orange",fontsize=8)
ax[1].axvline(1,ls=":",c="gray"); ax[1].text(1.15,12,"1 MOPS",fontsize=8)
ax[1].axvline(100,ls=":",c="gray"); ax[1].text(110,12,"100 MOPS",fontsize=8)
ax[1].text(3,40,"MC median = std −3.4dB\n(44.5dB @10MOPS/1MΩ → 7.1bit)",fontsize=7.5,color="tab:blue")
ax[1].set_xlabel("throughput per node (MOPS)"); ax[1].set_ylabel("SNR per layer (dB)")
ax[1].set_title("Hard limit 2: thermal noise vs throughput\n(SNR indep. of W; ∝R0^-½, ∝BW^-½)")
ax[1].legend(fontsize=8)
# 面板C: 单元容差 vs 输出误差
tolp=np.logspace(-4,0,60)
err=np.array(tolp)*100*np.sqrt(1.0)  # C5: 输出误差 ≈ 容差×1（Σ 抵消后）
ax[2].loglog(tolp*100, err, lw=2.5, color="tab:purple")
ax[2].axhline(0.195,ls=":",c="red"); ax[2].text(1.2,0.21,"0.195% ≈ INT8 LSB",color="red",fontsize=8)
ax[2].axhline(0.0078,ls="--",c="orange"); ax[2].text(1.2,0.009,"0.78% ≈ INT4/6 margin",color="orange",fontsize=8)
ax[2].axvline(0.1,ls=":",c="gray"); ax[2].text(0.11,8,"0.1% cell → INT8",fontsize=8)
ax[2].set_xlabel("cell conductance tolerance (%)"); ax[2].set_ylabel("output error (mean, Monte-Carlo C5)")
ax[2].set_title("Hard limit 3: device tolerance → accuracy\n(0.1% cells OR mismatch-aware training)")
plt.tight_layout(); plt.savefig(f"{OUT}/fig3_real_trilemma.pdf"); plt.savefig(f"{OUT}/fig3_real_trilemma.png",dpi=140)
print("fig3 (real trilemma) done")

# ── 图4: 规模地图（用 v6 最终面积数, 修正版）──
ns4=np.array([1e6,1e7,1e8,2.5e9,7e9,2.7e10])
a45=ns4*4.0/1e8; a7=ns4*0.1/1e8; a3=ns4*0.04/1e8
fig,ax=plt.subplots(figsize=(7.5,4.5))
ax.loglog(ns4/1e6,a45,"o-",lw=2,color="tab:red",label="45nm 1T1R (4µm²/param)")
ax.loglog(ns4/1e6,a7,"s-",lw=2,color="tab:orange",label="7nm (0.1µm²/param)")
ax.loglog(ns4/1e6,a3,"^-",lw=2,color="tab:green",label="3nm (0.04µm²/param)")
for xx,yy in zip(ns4/1e6,[2.5e9,7e9,2.7e10]):
    pass
ax.annotate("2.5B @45nm → 100 cm² (100 × 1cm² die)",xy=(2500,100),xytext=(40,300),arrowprops=dict(arrowstyle="->"),fontsize=8,color="tab:red")
ax.annotate("27B @45nm → 1080 cm² (≈126 reticle dies)",xy=(27000,1080),xytext=(300,2200),arrowprops=dict(arrowstyle="->"),fontsize=8,color="tab:red")
ax.annotate("27B @3nm → 10.9 cm² (≈1.3 reticle dies)",xy=(27000,11),xytext=(600,1.2),arrowprops=dict(arrowstyle="->"),fontsize=8,color="tab:green")
ax.set_xlim(0.8,60000); ax.set_ylim(0.8,3000)
ax.axhline(100,ls=":",c="gray"); ax.text(1.1,110,"100 cm² (100 × 1cm² die)",fontsize=8)
ax.axhline(8.6,ls="--",c="gray"); ax.text(1.1,9.5,"8.6 cm² = single reticle die",fontsize=8)
ax.set_xlabel("model size (M params)"); ax.set_ylabel("weight-array area (cm²)")
ax.set_title("Scaling map: 'params written into silicon' area tax\n(v6 design-space, 1T1R cell model)")
ax.legend(fontsize=9); ax.grid(alpha=0.3,which="both")
plt.tight_layout(); plt.savefig(f"{OUT}/fig4_scale.pdf"); plt.savefig(f"{OUT}/fig4_scale.png",dpi=140)
print("fig4 done")

# ── 图5: 设计窗口热图（R0 × 吞吐 → SNR, 论文核心图）──
# R7 修正: std 基公式 SNR=0.0577/√(3.1916·kT·BW·R0)（E[x²]=V²/3, E[Σ|w|]=W·0.7979）
R0s5=np.logspace(5,8,80)        # 100kΩ..100MΩ
ops5=np.logspace(3,9,80)        # 1kOPS..1GOPS
Z=np.zeros((len(ops5),len(R0s5)))
for i,op in enumerate(ops5):
    BW=op/2
    for j,R0x in enumerate(R0s5):
        Z[i,j]=20*np.log10(0.0577/np.sqrt(3.1916*kB*T*BW*R0x))
fig,ax=plt.subplots(figsize=(7.8,5))
cs=ax.pcolormesh(R0s5/1e3, ops5/1e6, Z, shading="auto", cmap="viridis",
                 norm=plt.Normalize(20,70))
ax.set_xscale("log"); ax.set_yscale("log")
ct=ax.contour(R0s5/1e3, ops5/1e6, Z, levels=[25.8,37.9,49.9],
              colors=["orange","cyan","red"], linestyles="--", linewidths=2)
cl=ax.clabel(ct, fmt={25.8:"INT4 (25.8dB)", 37.9:"6bit (37.9dB)", 49.9:"INT8 (49.9dB)"},
             fontsize=9, inline_spacing=4, colors=["orange","cyan","red"])
ax.set_xlabel("R0 (kΩ)"); ax.set_ylabel("throughput per node (MOPS)")
ax.set_title("Design window: per-layer SNR = f(R0, throughput)\n(color = SNR; dashed lines = bit-resolution contours)")
cb=fig.colorbar(cs); cb.set_label("SNR (dB)")
plt.tight_layout(); plt.savefig(f"{OUT}/fig5_design_window.pdf"); plt.savefig(f"{OUT}/fig5_design_window.png",dpi=140)
print("fig5 (design window) done")
print("ALL FIGS SAVED →", OUT)
