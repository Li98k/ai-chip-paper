# -*- coding: utf-8 -*-
"""三层神经网络 "参数即电阻" 布线原理图
L1(3 输入) --crossbar1--> L2(2 节点) --crossbar2--> L3(2 输出)
每条连线 = 一个电阻 R=R0/w；多线汇入一节点（虚拟地）做欧姆求和；
节点用 BJT（电流镜读出 + R_E 负反馈）读取；负权重用差分对（-x 支路）。
下标一律用 ASCII（x1/x2/x3, y1/y2, z1/z2, w_i·x_i）以避免 CJK 字体缺字。
"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
import os
plt.rcParams["font.sans-serif"]=["Noto Sans CJK SC","Noto Sans CJK JP","Droid Sans Fallback","WenQuanYi Zen Hei","SimHei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"]=False
OUT=os.path.dirname(os.path.abspath(__file__))+"/figs"; os.makedirs(OUT,exist_ok=True)

# ── 权重（与 sim_v11 一致）──
W1=np.array([[ 0.8, 0.3,-0.2],[-0.5, 0.7, 0.4]])   # (2 输出 × 3 输入)
W2=np.array([[ 0.6,-0.4],[ 0.9, 0.2]])              # (2 输出 × 2 输入)
R0=1e6
def Rk(w): return R0/abs(w)/1e3

fig,ax=plt.subplots(figsize=(15.5,9.2))
ax.set_xlim(0,15.5); ax.set_ylim(0,9.2); ax.axis("off")
C_POS,C_NEG="k","crimson"

# ── 绘图基元 ──
def rez_v(ax,x,y,h=0.5,nz=4,color="k",lw=1.6,z=5):
    y0,y1=y-h/2,y+h/2; dx=0.14; xs=[x];ys=[y0]; n=nz*2
    for i in range(1,n):
        yy=y0+(y1-y0)*i/n; xx=x+dx if i%2==1 else x-dx
        xs.append(xx);ys.append(yy)
    xs.append(x);ys.append(y1)
    ax.plot(xs,ys,color=color,lw=lw,solid_capstyle="round",zorder=z)
    return y0,y1

def rez_h(ax,x,y,w=0.5,nz=4,color="k",lw=1.6,z=5):
    x0,x1=x-w/2,x+w/2; dy=0.14; ys=[y];xs=[x0]; n=nz*2
    for i in range(1,n):
        xx=x0+(x1-x0)*i/n; yy=y+dy if i%2==1 else y-dy
        ys.append(yy);xs.append(xx)
    xs.append(x1);ys.append(y)
    ax.plot(xs,ys,color=color,lw=lw,solid_capstyle="round",zorder=z)

def vsource(ax,x,y,r=0.32,label="",sub=""):
    ax.add_patch(Circle((x,y),r,fill=False,color="k",lw=1.6,zorder=5))
    ax.text(x,y+r*0.4,"+",fontsize=11,ha="center",va="center",zorder=6)
    ax.text(x,y-r*0.45,"-",fontsize=11,ha="center",va="center",zorder=6)
    ax.text(x+r+0.08,y+r+0.28,label,fontsize=12,fontweight="bold",va="center")
    if sub: ax.text(x+r+0.08,y+r-0.14,sub,fontsize=8,va="center",color="dimgray")

def vground_glyph(ax,x,y,s=0.13,color="k",lw=1.2):
    ax.add_patch(Circle((x,y),s,fill=False,color=color,lw=lw,zorder=6))
    ax.plot([x,x],[y-s,y-s-0.10],color=color,lw=lw,zorder=6)
    for i,ww in enumerate([0.16,0.10,0.05]):
        yy=y-s-0.10-0.055*i
        ax.plot([x-ww,x+ww],[yy,yy],color=color,lw=lw,zorder=6)

def bjt_glyph(ax,x,y,s=0.5,color="k",lw=1.5):
    ax.plot([x,x],[y-s*0.4,y+s*0.4],color=color,lw=lw+0.7,zorder=6)   # base bar
    ax.plot([x,x+s*0.5],[y+s*0.18,y+s*0.48],color=color,lw=lw,zorder=6)  # collector
    ax.plot([x,x+s*0.5],[y-s*0.12,y-s*0.42],color=color,lw=lw,zorder=6)  # emitter
    ax.annotate("",xy=(x+s*0.5,y-s*0.42),xytext=(x+s*0.30,y-s*0.30),
                arrowprops=dict(arrowstyle="-|>",color=color,lw=1.1),zorder=6)

def readout(ax,cx,cy,out_lab,top_wire=True):
    # 外接方框（读出单元：虚拟地 + BJT 电流镜 + R_E）
    ax.add_patch(FancyBboxPatch((cx-0.62,cy-0.62),1.24,1.24,
                 boxstyle="round,pad=0.02,rounding_size=0.08",
                 fill=True,fc="#f7f7f7",ec="k",lw=1.3,zorder=4))
    if top_wire: ax.plot([cx,cx],[cy+0.62,cy+0.92],color="k",lw=1.4,zorder=5)
    vground_glyph(ax,cx,cy+0.42,s=0.11)
    ax.text(cx+0.20,cy+0.42,"虚拟地",fontsize=7.5,va="center",zorder=6)
    bjt_glyph(ax,cx-0.18,cy-0.05,s=0.5)
    ax.text(cx+0.42,cy+0.02,"BJT\n电流镜",fontsize=7.5,va="center",ha="left",zorder=6)
    rez_v(ax,cx+0.30,cy-0.40,h=0.28,nz=3)            # R_E
    ax.text(cx+0.52,cy-0.40,"R_E",fontsize=7.5,va="center",zorder=6)
    ax.plot([cx-0.62,cx-0.95],[cy-0.05,cy-0.05],color="k",lw=1.4,zorder=5)  # 输出(左)
    ax.plot([cx-0.95,cx-0.95],[cy-0.05,cy+0.05],color="k",lw=1.4,zorder=5)
    ax.text(cx-1.02,cy+0.02,out_lab,fontsize=11,fontweight="bold",ha="right",va="center",zorder=6)

def label_rez(ax,x,y,txt,dy=0.34,color="k"):
    ax.text(x,y+dy,txt,fontsize=7.3,ha="center",va="bottom",color=color,zorder=7,
            bbox=dict(boxstyle="round,pad=0.12",fc="white",ec="none",alpha=0.85))

# ══ 左列：L1 输入 ══
L1x=1.0; L1y=[7.2,5.2,3.2]
for i,(y,lab) in enumerate(zip(L1y,["x1","x2","x3"])):
    vsource(ax,L1x,y,label=lab,sub="0~100mV")
ax.text(L1x,8.15,"L1 输入层",fontsize=13,fontweight="bold",ha="center")

# ══ crossbar 1（L1→L2）：竖总线 x=3.3,4.5，横总线 y=7.2,5.2,3.2 ══
cb1x=[3.3,4.5]; cb1y=L1y
for xv in cb1x:
    ax.plot([xv,xv],[cb1y[2]-0.28,cb1y[0]+0.28],color="k",lw=1.4,zorder=3)
for yv in cb1y:
    ax.plot([L1x+0.32,cb1x[1]+0.28],[yv,yv],color="k",lw=1.4,zorder=3)
# 电阻（竖置，打断竖总线）
for j,jv in enumerate(cb1x):
    for i,iv in enumerate(cb1y):
        w=W1[j,i]; col=C_POS if w>=0 else C_NEG
        rez_v(ax,jv,iv,h=0.46,color=col)
        lab=f"R={Rk(w):.0f}k"
        if w<0: lab=f"-{Rk(w):.0f}k"
        label_rez(ax,jv,iv,lab,dy=0.26,color=col)
ax.text((cb1x[0]+cb1x[1])/2,8.15,"L2 隐藏层 (2 节点)",fontsize=12,fontweight="bold",ha="center")

# L2 读出单元（竖总线底端之下）
readout(ax,cb1x[0],1.55,"y1")
readout(ax,cb1x[1],1.55,"y2")
ax.plot([cb1x[0],cb1x[0]],[cb1y[2]-0.28,1.55+0.92],color="k",lw=1.4,zorder=5)
ax.plot([cb1x[1],cb1x[1]],[cb1y[2]-0.28,1.55+0.92],color="k",lw=1.4,zorder=5)

# ══ L2 输出 → crossbar2 横总线（布线 y1→y=5.5, y2→y=4.0）══
y1b,y2b=5.5,4.0
ax.plot([cb1x[0]-0.95,5.9],[1.5,1.5],color="tab:blue",lw=1.5,zorder=5)
ax.plot([5.9,5.9],[1.5,y1b],color="tab:blue",lw=1.5,zorder=5)
ax.plot([cb1x[1]-0.95,6.25],[1.3,1.3],color="tab:green",lw=1.5,zorder=5)
ax.plot([6.25,6.25],[1.3,y2b],color="tab:green",lw=1.5,zorder=5)
ax.text(5.55,3.3,"y1",fontsize=10,color="tab:blue",fontweight="bold")
ax.text(5.9,2.7,"y2",fontsize=10,color="tab:green",fontweight="bold")

# ══ crossbar 2（L2→L3）：竖总线 x=8.0,9.2，横总线 y=5.5,4.0 ══
cb2x=[8.0,9.2]; cb2y=[y1b,y2b]
for xv in cb2x:
    ax.plot([xv,xv],[cb2y[1]-0.28,cb2y[0]+0.28],color="k",lw=1.4,zorder=3)
for yv in cb2y:
    ax.plot([6.4,xv+0.28],[yv,yv],color="k",lw=1.4,zorder=3)
for j,jv in enumerate(cb2x):
    for i,iv in enumerate(cb2y):
        w=W2[j,i]; col=C_POS if w>=0 else C_NEG
        rez_v(ax,jv,iv,h=0.46,color=col)
        lab=f"R={Rk(w):.0f}k"
        if w<0: lab=f"-{Rk(w):.0f}k"
        label_rez(ax,jv,iv,lab,dy=0.26,color=col)
ax.text((cb2x[0]+cb2x[1])/2,8.15,"L3 输出层 (2 节点)",fontsize=12,fontweight="bold",ha="center")

# L3 读出
readout(ax,cb2x[0],2.35,"z1")
readout(ax,cb2x[1],2.35,"z2")
ax.plot([cb2x[0],cb2x[0]],[cb2y[1]-0.28,2.35+0.92],color="k",lw=1.4,zorder=5)
ax.plot([cb2x[1],cb2x[1]],[cb2y[1]-0.28,2.35+0.92],color="k",lw=1.4,zorder=5)

# ══ 标题与说明 ══
ax.text(7.75,8.95,"三层神经网络 “参数即电阻” 布线原理图（3→2→2，R0=1MΩ）",
        fontsize=15,fontweight="bold",ha="center")
ax.text(0.4,0.55,
 "① 布线=电阻=参数：R=R0/w（G=w/R0），电阻值由模型参数直接算出\n"
 "② 多条连线汇入一节点 → 等效电导 G_node=(1/R0)·Σ w_i·x_i 随输入变化\n"
 "③ 节点电流 I=(1/R0)·Σ w_i·x_i（虚拟地·欧姆求和，天然线性）\n"
 "④ BJT=电流镜读出 + R_E 发射极负反馈线性化（工作点 IC0=200µA）\n"
 "⑤ 负权重（红色）用差分对实现：接 -x 支路（x 与 -x 双输入）",
 fontsize=9.5,va="bottom",ha="left",
 bbox=dict(boxstyle="round,pad=0.4",fc="#fffbe6",ec="goldenrod",lw=1.2))

# 图例（正/负权重）
ax.plot([12.3,12.9],[8.4,8.4],color=C_POS,lw=2); rez_h(ax,12.6,8.4,w=0.3,nz=3)
ax.text(13.0,8.4,"正权重 R=R0/w",fontsize=8.5,va="center")
ax.plot([12.3,12.9],[7.9,7.9],color=C_NEG,lw=2); rez_h(ax,12.6,7.9,w=0.3,nz=3,color=C_NEG)
ax.text(13.0,7.9,"负权重（差分对 -x）",fontsize=8.5,va="center",color=C_NEG)
ax.text(11.2,8.4,"图例",fontsize=9,fontweight="bold")

plt.tight_layout()
fig.savefig(f"{OUT}/fig3layer_wiring.png",dpi=150,bbox_inches="tight")
fig.savefig(f"{OUT}/fig3layer_wiring.pdf",bbox_inches="tight")
print("三层布线原理图 →",f"{OUT}/fig3layer_wiring.png")
