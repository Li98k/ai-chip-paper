# -*- coding: utf-8 -*-
"""图 8: 最优读出前端 —— 电流模差分读出 + 电荷采样（§4.7 方案 C/D）
左→右：① crossbar 虚拟地节点(电流和, 正/负支路 I±) → ② 差分电流缓冲(电流镜,
  I+−I-, CMR~40dB) → ③ 电荷采样 C(V=I·τ/C, 无 R_f 热噪声) → ④ ADC→下一层
下标 ASCII；CHECK=1 时用渲染器包围盒自检重叠（部分重叠 12%~92%）。
"""
import numpy as np, matplotlib, os
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
plt.rcParams["font.sans-serif"]=["Noto Sans CJK SC","WenQuanYi Zen Hei","SimHei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"]=False
OUT=os.path.dirname(os.path.abspath(__file__))+"/figs"; os.makedirs(OUT,exist_ok=True)

fig,ax=plt.subplots(figsize=(16,9.6)); ax.set_xlim(0,15.5); ax.set_ylim(0,9.4); ax.axis("off")
C_IN,C_NOD,C_AMP,C_CH="#1f5fa8","#a83232","#6a3aa0","#2c7a2c"
def wire(x1,y1,x2,y2,color="k",lw=1.7,ls="-"): ax.plot([x1,x2],[y1,y2],color=color,lw=lw,linestyle=ls,zorder=2)
def node(x,y,r=0.055): ax.add_patch(Circle((x,y),r,color="k",zorder=6))
def iarrow(x1,y1,x2,y2,color="k",lw=1.7,fs=15): ax.annotate("",xy=(x2,y2),xytext=(x1,y1),
    arrowprops=dict(arrowstyle="-|>",color=color,lw=lw,mutation_scale=fs),zorder=4)
def gnd(x,y,s=0.13,color="k"):
    ax.add_patch(Circle((x,y),s,fill=False,color=color,lw=1.2,zorder=6))
    ax.plot([x,x],[y-s,y-s-0.1],color=color,lw=1.2,zorder=6)
    for i,w in enumerate([0.17,0.11,0.05]):
        yy=y-s-0.1-0.055*i;ax.plot([x-w,x+w],[yy,yy],color=color,lw=1.2,zorder=6)
def cap_v(x,y,ph=0.30):  # 竖直极板电容器（信号水平方向，极板竖直）
    for dx in (-0.09,0.09):
        ax.plot([x+dx,x+dx],[y-ph/2,y+ph/2],color="k",lw=2.2,zorder=5)

# ══ 标题 ══
ax.text(7.75,9.02,"最优读出前端：电流模差分读出 + 电荷采样（消解 BJT/MOS 控制模态失配）",
        fontsize=14.5,fontweight="bold",ha="center")

# ══ 左：crossbar 虚拟地节点（电流和, 正/负支路）══
NX,NY=2.6,6.15
ax.text(NX,8.45,"crossbar 虚拟地节点（电流和）",fontsize=10,fontweight="bold",ha="center",color=C_NOD)
# 节点
node(NX,NY,r=0.07)
gnd(NX,NY,s=0.13,color=C_NOD)
ax.text(NX,NY-0.34,"≈0V",fontsize=9,ha="center",color=C_NOD,fontweight="bold")
# 正支路（上路 y=7.05）
wire(NX,NY,NX,7.05); wire(NX,7.05,5.4,7.05,color=C_IN,lw=2.0)
iarrow(4.9,7.05,5.25,7.05,color=C_IN,fs=13)
ax.text(3.9,7.42,"I+ = (1/R0)·Σ w_j+·x_j   [A]",fontsize=8.6,ha="center",color=C_IN,fontweight="bold")
ax.text(3.9,6.62,"（正权重支路）",fontsize=8.0,ha="center",color="#555")
# 负支路（下路 y=5.25）
wire(NX,NY,NX,5.25); wire(NX,5.25,5.4,5.25,color=C_IN,lw=2.0)
iarrow(4.9,5.25,5.25,5.25,color=C_IN,fs=13)
ax.text(3.9,4.68,"I− = (1/R0)·Σ w_j−·x_j   [A]",fontsize=8.6,ha="center",color=C_IN,fontweight="bold")
ax.text(3.9,5.05,"（负权重支路）",fontsize=8.0,ha="center",color="#555")

# ══ 中：差分电流缓冲（方框）══
BX,BY,BW,BH=5.4,4.35,3.5,3.55
ax.add_patch(FancyBboxPatch((BX,BY),BW,BH,boxstyle="round,pad=0.02,rounding_size=0.12",
             fill=True,fc="#f5f1fb",ec=C_AMP,lw=1.6,zorder=1))
ax.text(BX+BW/2,BY+BH-0.22,"差分电流缓冲（电流镜）",fontsize=10.5,ha="center",va="top",
        fontweight="bold",color=C_AMP)
ax.text(BX+BW/2,BY+BH-0.78,"上：I+ 镜 → I+ 出",fontsize=8.6,ha="center",color="#4a2560")
ax.text(BX+BW/2,BY+BH-1.12,"下：I− 镜 → I− 出",fontsize=8.6,ha="center",color="#4a2560")
ax.text(BX+BW/2,BY+0.62,"共模抑制 CMR≈40dB",fontsize=9.0,ha="center",fontweight="bold",color=C_AMP)
ax.text(BX+BW/2,BY+0.22,"R0 共模漂移 / 温度 / offset 被抵消",fontsize=7.8,ha="center",color="#4a2560")
# 输入（左）
wire(5.4,7.05,5.4,7.05); wire(5.4,5.25,5.4,5.25)
# 输出（右）I_out = I+ - I-
wire(8.9,6.15,9.6,6.15,color=C_AMP,lw=2.0)
iarrow(9.25,6.15,9.55,6.15,color=C_AMP,fs=13)
ax.text(10.05,6.5,"I_out = I+ − I−",fontsize=9.0,ha="center",fontweight="bold",color=C_AMP)
ax.text(10.05,5.80,"（电流模, 未做 I→V）",fontsize=7.8,ha="center",color="#555")

# ══ 右：电荷采样 C（电流模 S/H, 对地）══
CX,CY=11.3,6.15
wire(9.6,6.15,CX,6.15); node(CX,CY,r=0.06)
# 电容器（对地, 竖直极板, 极板水平）
cap_v(CX,CY-0.42,ph=0.34)
ax.plot([CX,CX],[CY,CY-0.22],color="k",lw=1.7,zorder=5)
ax.plot([CX,CX],[CY-0.62,CY-0.82],color="k",lw=1.7,zorder=5)
gnd(CX,CY-0.82,s=0.12)
ax.text(CX+0.30,CY-0.42,"C",fontsize=11,ha="left",va="center",fontweight="bold")
ax.text(CX+0.12,CY+0.34,"I_out 流入 τ → 充电",fontsize=8.2,ha="left",color="#0a5",fontweight="bold")
ax.text(CX+0.12,CY-1.25,"V_out = I_out·τ/C  [V]",fontsize=8.8,ha="left",color="#0a5",fontweight="bold")
ax.text(CX+0.12,CY-1.56,"无 R_f 热噪声, 噪声 kT/C≈0.02µV",fontsize=7.6,ha="left",color="#555")

# ══ 最右：ADC → 下一层 ══
NX2,NY2,NW2,NH2=13.3,5.55,1.9,1.2
ax.add_patch(FancyBboxPatch((NX2,NY2),NW2,NH2,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#e7f6e7",ec=C_CH,lw=1.6,zorder=3))
wire(CX+0.12,CY,NX2,CY); iarrow(12.9,CY,NX2-0.02,CY,color=C_CH,fs=12)
ax.text(NX2+NW2/2,NY2+NH2-0.2,"ADC → 下一层",fontsize=9.5,fontweight="bold",ha="center",va="top",color="#1c5c1c")
ax.text(NX2+NW2/2,NY2+0.4,"输入 = V_out",fontsize=8.6,ha="center",va="center",color="#1c5c1c")

# ══ 下方：信号传输流程（①②③④）══
FY,FH=1.5,1.9
ax.add_patch(FancyBboxPatch((0.5,FY),15.0,FH,boxstyle="round,pad=0.02,rounding_size=0.12",
             fill=True,fc="#f7fbff",ec=C_IN,lw=1.3,zorder=1))
ax.text(0.7,FY+FH-0.18,"信号传输流程（全程电流模，差分抵消共模，无阻抗转换）",
        fontsize=10.5,fontweight="bold",ha="left",va="top",color="#134")
fy=FY+0.30; fbh=1.05
def fbox(x,w,txt,ec):
    ax.add_patch(FancyBboxPatch((x,fy),w,fbh,boxstyle="round,pad=0.02,rounding_size=0.08",
                 fill=True,fc="white",ec=ec,lw=1.3,zorder=3))
    ax.text(x+w/2,fy+fbh/2,txt,fontsize=8.6,ha="center",va="center",zorder=4)
fbox(0.70,2.95,"① crossbar 电流和\nI± = (1/R0)Σw·x  [A]",C_IN)
fbox(3.85,3.35,"② 差分电流缓冲\nI_out = I+ − I−  [A]\n(CMR≈40dB, 共模抵消)",C_AMP)
fbox(7.40,3.35,"③ 电荷采样 C\nV_out = I_out·τ/C  [V]\n(无 R_f 噪声, kT/C)",C_CH)
fbox(10.95,4.0,"④ ADC → 下一层\n增益管按节点选：BJT(45nm)/MOS(7/3nm)", "#1c5c1c")
for x2 in [3.68,7.22,10.78]:
    iarrow(x2-0.02,fy+fbh/2,x2+0.26,fy+fbh/2,color="#333",fs=14)

# ══ 最底：三种读出对比 ══
CY0,CH0=0.3,1.0
ax.add_patch(FancyBboxPatch((0.5,CY0),4.6,CH0,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#fdeeee",ec="#b23",lw=1.2,zorder=2))
ax.text(2.8,CY0+CH0-0.16,"单端 BJT",fontsize=9.2,ha="center",va="top",fontweight="bold",color="#7a2020")
ax.text(2.8,CY0+0.28,"45nm 优选 · 电流控制本征匹配 · 1/f 低",fontsize=8.2,ha="center",va="center",color="#7a2020")
ax.add_patch(FancyBboxPatch((5.4,CY0),4.6,CH0,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#eef2fb",ec=C_IN,lw=1.2,zorder=2))
ax.text(7.7,CY0+CH0-0.16,"单端 MOS 跨阻 TIA",fontsize=9.2,ha="center",va="top",fontweight="bold",color="#134")
ax.text(7.7,CY0+0.28,"7/3nm 必用 · 纯 CMOS 可得 · 0 DC 负载",fontsize=8.2,ha="center",va="center",color="#134")
ax.add_patch(FancyBboxPatch((10.3,CY0),5.2,CH0,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#e9f5e9",ec="#2c7a2c",lw=1.5,zorder=2))
ax.text(12.9,CY0+CH0-0.16,"★ 差分电流模（推荐）",fontsize=9.2,ha="center",va="top",fontweight="bold",color="#1c5c1c")
ax.text(12.9,CY0+0.28,"节点无关 · 消解模态失配 · 共模抵消 + 电荷采样零 R_f",fontsize=8.2,ha="center",va="center",color="#1c5c1c")

# ── CHECK 模式：渲染器包围盒自检（部分重叠 12%~92%）──
if os.environ.get("CHECK"):
    fig.canvas.draw(); rend=fig.canvas.get_renderer()
    boxes=[]
    for o in ax.texts:
        try: boxes.append(("TXT",o.get_text().replace("\n","⏎")[:22],o.get_window_extent(renderer=rend)))
        except Exception: pass
    for o in ax.patches:
        try: boxes.append(("PCH",type(o).__name__,o.get_window_extent(renderer=rend)))
        except Exception: pass
    def inter(a,b): return max(0,min(a.x1,b.x1)-max(a.x0,b.x0))*max(0,min(a.y1,b.y1)-max(a.y0,b.y0))
    def area(b): return max(1e-6,(b.x1-b.x0)*(b.y1-b.y0))
    n=0
    pchs=[b for t,_,b in boxes if t=="PCH"]
    def center_in_pch(b):
        cx,cy=(b.x0+b.x1)/2,(b.y0+b.y1)/2
        return any(bb.x0-3<=cx<=bb.x1+3 and bb.y0-3<=cy<=bb.y1+3 for bb in pchs)
    for a in range(len(boxes)):
        for c in range(a+1,len(boxes)):
            t1,l1,b1=boxes[a]; t2,l2,b2=boxes[c]
            if not l1.strip() or not l2.strip(): continue
            if (t1=="TXT" and center_in_pch(b1)) or (t2=="TXT" and center_in_pch(b2)): continue
            ov=inter(b1,b2); r=ov/min(area(b1),area(b2))
            if ov>12 and 0.12<=r<=0.92:
                n+=1; print(f"[{n}] {t1}«{l1}» × {t2}«{l2}»  {100*r:.0f}%")
    print(f"共 {n} 处真实重叠（已排除框内标注/空文字）")

plt.tight_layout()
fig.savefig(f"{OUT}/fig_readout_diff.png",dpi=150,bbox_inches="tight")
fig.savefig(f"{OUT}/fig_readout_diff.pdf",bbox_inches="tight")
print("最优读出前端图 →",f"{OUT}/fig_readout_diff.png")
