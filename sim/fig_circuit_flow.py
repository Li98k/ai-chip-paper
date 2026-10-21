# -*- coding: utf-8 -*-
"""电路图实例：神经元之间的信号传递 = 权重电阻 + BJT 放大（干净布局版）
左→右 传输流程（集中到下方流程带 ①→②→③→④）：
  ① 前层神经元 x_j → ② 过权重电阻 R_j=R0/w_j 变电流 I_j → ③ 虚拟地节点求和
  I=(1/R0)Σw_j·x_j → ④ BJT 放大读出 y=Σw_j·x_j → 下一层神经元
垂直预算（不重叠）：标题[8.8,9.4] / 电路[4.0,8.85] / 流程带[1.5,3.4] / 对比框[0.3,1.3]
下标 ASCII；CHECK=1 时用渲染器包围盒自检重叠。
"""
import numpy as np, matplotlib, os
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
plt.rcParams["font.sans-serif"]=["Noto Sans CJK SC","Noto Sans CJK JP","Droid Sans Fallback","WenQuanYi Zen Hei","SimHei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"]=False
OUT=os.path.dirname(os.path.abspath(__file__))+"/figs"; os.makedirs(OUT,exist_ok=True)

fig,ax=plt.subplots(figsize=(16,9.6)); ax.set_xlim(0,15.5); ax.set_ylim(0,9.4); ax.axis("off")
C_IN,C_NOD,C_AMP="#1f5fa8","#a83232","#6a3aa0"
def wire(x1,y1,x2,y2,color="k",lw=1.7,ls="-"): ax.plot([x1,x2],[y1,y2],color=color,lw=lw,linestyle=ls,zorder=2)
def node(x,y,r=0.055): ax.add_patch(Circle((x,y),r,color="k",zorder=6))
def iarrow(x1,y1,x2,y2,color="k",lw=1.7,fs=15): ax.annotate("",xy=(x2,y2),xytext=(x1,y1),
    arrowprops=dict(arrowstyle="-|>",color=color,lw=lw,mutation_scale=fs),zorder=4)
def rez_h(ax,x,y,w=0.5,color="k"):
    x0,x1=x-w/2,x+w/2;dy=0.13;ys=[y];xs=[x0];n=8
    for i in range(1,n):
        xx=x0+(x1-x0)*i/n;yy=y+dy if i%2 else y-dy;ys.append(yy);xs.append(xx)
    xs.append(x1);ys.append(y);ax.plot(xs,ys,color=color,lw=1.7,zorder=5)
def vsrc(x,y):
    ax.add_patch(Circle((x,y),0.30,fill=False,color=C_IN,lw=1.8,zorder=5))
    ax.text(x,y+0.12,"+",fontsize=11,ha="center",va="center",color=C_IN,zorder=6)
    ax.text(x,y-0.14,"-",fontsize=11,ha="center",va="center",color=C_IN,zorder=6)
def gnd(x,y,s=0.13,color="k"):
    ax.add_patch(Circle((x,y),s,fill=False,color=color,lw=1.2,zorder=6))
    ax.plot([x,x],[y-s,y-s-0.1],color=color,lw=1.2,zorder=6)
    for i,w in enumerate([0.17,0.11,0.05]):
        yy=y-s-0.1-0.055*i;ax.plot([x-w,x+w],[yy,yy],color=color,lw=1.2,zorder=6)
def bjt(x,y,s=1.0):
    ax.plot([x,x],[y-0.6*s,y+0.6*s],color="k",lw=2.6,zorder=6)
    cb=(x+0.7*s,y+0.6*s); eb=(x+0.7*s,y-0.6*s)
    wire(x,y+0.34*s,cb[0],cb[1],lw=1.7); wire(x,y-0.20*s,eb[0],eb[1],lw=1.7)
    iarrow(x+0.5*s,y-0.45*s,eb[0],eb[1],lw=1.3,fs=13)
    return {"base":(x,y),"col":cb,"em":eb}

# ══ 标题 ══
ax.text(7.75,9.05,"电路图实例：神经元之间的信号传递 = 权重电阻 + BJT 放大（3 输入→1 节点）",
        fontsize=15,fontweight="bold",ha="center")

# ══ 左：前层神经元（信号源）══
ax.text(1.5,8.55,"前层神经元 (信号源 x_j, 0~100mV)",fontsize=10,fontweight="bold",ha="center",color=C_IN)
ys=[7.7,6.3,4.9]; labs=["x1 [V]","x2 [V]","x3 [V]"]
for y,lab in zip(ys,labs):
    vsrc(1.5,y); gnd(1.5,y-0.44,s=0.12); ax.text(1.5,y-0.96,lab,fontsize=11.5,fontweight="bold",ha="center")

# ══ 权重电阻（每路一条，R_j=R0/w_j）══
RL=["R1 = R0/w1","R2 = R0/w2","R3 = R0/w3"]
for y,rl in zip(ys,RL):
    wire(1.8,y,3.3,y); rez_h(ax,3.95,y,w=1.3); wire(4.6,y,5.2,y)
    ax.text(3.95,y+0.30,rl,fontsize=8.6,ha="center",color="#0a5")
    iarrow(4.15,y,4.55,y)
    ax.text(4.35,y-0.30,"I_j",fontsize=8.2,ha="center",color="#0a5")
# （“x_j 过权重电阻→I_j”说明已并入底部流程带 ②，避免压 x3 源）

# ══ 中：虚拟地求和节点 ══
RAILX=5.2
wire(RAILX,ys[2],RAILX,ys[0],color=C_NOD,lw=2.0)
gnd(RAILX,ys[2],s=0.13,color=C_NOD)
ax.text(RAILX,ys[2]-0.32,"虚拟地 (≈0V)",fontsize=9,ha="center",color=C_NOD,fontweight="bold")
for y in ys: node(RAILX,y)
ax.text(RAILX,ys[0]+0.28,"Σ",fontsize=17,ha="center",va="bottom",color=C_NOD,fontweight="bold")
ax.text(RAILX,ys[0]+0.92,"所有连线电流在此求和\nI = (1/R0)·Σ w_j·x_j",
        fontsize=9.0,ha="center",va="bottom",color=C_NOD,
        bbox=dict(boxstyle="round,pad=0.32",fc="#ffecec",ec=C_NOD,lw=1.1))

# ══ BJT 放大读出级（方框）══
BX,BY,BW,BH=6.9,4.0,3.3,4.85
ax.add_patch(FancyBboxPatch((BX,BY),BW,BH,boxstyle="round,pad=0.02,rounding_size=0.12",
             fill=True,fc="#f5f1fb",ec=C_AMP,lw=1.6,zorder=1))
ax.text(BX+BW/2,BY+BH-0.24,"BJT 放大读出级（R_E 线性化）",fontsize=10.5,ha="center",va="top",
        fontweight="bold",color=C_AMP)
B=bjt(7.6,6.3,s=1.15)
# 节点 → 基极（输入）
wire(RAILX,6.3,B["base"][0],6.3); iarrow(6.3,6.3,7.3,6.3,color=C_AMP)
ax.text(6.55,6.55,"I (求和电流)",fontsize=8.0,ha="center",color=C_AMP)
# 基极偏置
wire(7.6,6.3,7.6,8.45)
ax.text(7.78,7.4,"V_BIAS (工作点 IC0=200µA)",fontsize=7.8,ha="left",color="#555")
# 集电极 → 电流源
cx,cy=B["col"]; wire(cx,cy,cx,cy+0.55); ax.add_patch(Circle((cx,cy+0.55),0.28,fill=False,ec="k",lw=1.5,zorder=5))
iarrow(cx,cy+0.6,cx,cy+0.85,fs=12)
ax.add_patch(FancyBboxPatch((cx-0.55,cy+0.85),1.1,0.6,boxstyle="round,pad=0.01",fc="white",ec="k",lw=1.0,zorder=5))
ax.text(cx,cy+1.15,"电流源\nVCC",fontsize=8,ha="center",va="center",zorder=6)
# 发射极 → R_E → 输出 y
ex,ey=B["em"]; rez_h(ax,ex,ey-0.38,w=0.5)
ax.text(ex-0.42,ey-0.38,"R_E",fontsize=8.5,ha="right",va="center")
ax.plot([ex,ex],[ey,ey-0.18],color="k",lw=1.7,zorder=5); ax.plot([ex,ex],[ey-0.56,ey-0.72],color="k",lw=1.7,zorder=5)
node(ex,ey-0.72)
wire(ex,ey-0.72,11.0,ey-0.72); iarrow(10.3,ey-0.72,10.75,ey-0.72,color=C_AMP)
ax.text(10.55,5.05,"y",fontsize=12,ha="center",fontweight="bold",color=C_AMP)
ax.text(8.55,4.42,"跨导被 R_E 钳住、与 β 无关\n→ 全摆幅线性 <0.2%",fontsize=7.8,ha="center",color="#4a2560")

# ══ 右：下一层神经元 ══
NX,NY,NW,NH=11.0,5.7,2.9,1.1
ax.add_patch(FancyBboxPatch((NX,NY),NW,NH,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#e7f6e7",ec="#2c7a2c",lw=1.6,zorder=3))
wire(11.0,ey-0.72,11.0,NY)
ax.text(NX+NW/2,NY+NH-0.2,"下一层神经元",fontsize=11,fontweight="bold",ha="center",va="top",color="#1c5c1c")
ax.text(NX+NW/2,NY+0.42,"输入 = y （不读不写，\n直接传模拟信号）",fontsize=9,ha="center",va="center",color="#1c5c1c")

# ══ 下方：信号传输流程（①②③④）══
FY,FH=1.5,1.9
ax.add_patch(FancyBboxPatch((0.5,FY),15.0,FH,boxstyle="round,pad=0.02,rounding_size=0.12",
             fill=True,fc="#f7fbff",ec=C_IN,lw=1.3,zorder=1))
ax.text(0.7,FY+FH-0.18,"信号传输流程（一次电压施加，信号直通，无数据搬运）",
        fontsize=10.5,fontweight="bold",ha="left",va="top",color="#134")
fy=FY+0.30; fbh=1.05
def fbox(x,w,txt,ec):
    ax.add_patch(FancyBboxPatch((x,fy),w,fbh,boxstyle="round,pad=0.02,rounding_size=0.08",
                 fill=True,fc="white",ec=ec,lw=1.3,zorder=3))
    ax.text(x+w/2,fy+fbh/2,txt,fontsize=9.0,ha="center",va="center",zorder=4)
fbox(0.70,2.55,"① 前层神经元\nx_j  [V]",C_IN)
fbox(3.85,2.35,"② 过权重电阻\nI_j = w_j·x_j/R0  [A]",C_IN)
ax.text(6.55,fy+fbh/2,"Σ",fontsize=17,ha="center",va="center",color=C_NOD,fontweight="bold")
fbox(6.90,2.55,"③ 虚拟地节点求和\nI = (1/R0)Σ w_j·x_j  [A]",C_NOD)
fbox(9.95,2.25,"④ BJT 放大 (×R0)\ny = Σ w_j·x_j  [V]",C_AMP)
fbox(12.70,2.25,"下一层神经元\n输入 = y", "#2c7a2c")
for x2 in [3.25,6.22,9.45,12.20]:
    iarrow(x2-0.02,fy+fbh/2,x2+0.30,fy+fbh/2,color="#333",fs=14)

# ══ 最底：传统数字 vs 本电路 ══
CY,CH=0.3,1.0
ax.add_patch(FancyBboxPatch((0.5,CY),7.5,CH,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#fdeeee",ec="#b23",lw=1.2,zorder=2))
ax.text(4.25,CY+CH-0.16,"传统数字 (GPU)：神经元 → 神经元",fontsize=9.2,ha="center",va="top",fontweight="bold",color="#7a2020")
ax.text(4.25,CY+0.28,"读内存 → 乘法器 MAC → 写内存   （能耗主体=数据搬运）",fontsize=8.8,ha="center",va="center",color="#7a2020")
ax.add_patch(FancyBboxPatch((8.5,CY),7.0,CH,boxstyle="round,pad=0.02,rounding_size=0.1",
             fill=True,fc="#e9f5e9",ec="#2c7a2c",lw=1.2,zorder=2))
ax.text(12.0,CY+CH-0.16,"本电路：神经元 → 神经元",fontsize=9.2,ha="center",va="top",fontweight="bold",color="#1c5c1c")
ax.text(12.0,CY+0.28,"过权重电阻 → 节点求和 → BJT 放大   （一次直通，无内存读/写）",fontsize=8.4,ha="center",va="center",color="#1c5c1c")

# ── CHECK 模式：渲染器包围盒自检（部分重叠 12%~92%）──
if os.environ.get("CHECK"):
    fig.canvas.draw(); rend=fig.canvas.get_renderer(); inv=ax.transData.inverted()
    boxes=[]
    for i,o in enumerate(ax.texts):
        try: boxes.append(("TXT",o.get_text().replace("\n","⏎")[:20],o.get_window_extent(renderer=rend)))
        except Exception: pass
    for i,o in enumerate(ax.patches):
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
fig.savefig(f"{OUT}/fig_circuit_flow.png",dpi=150,bbox_inches="tight")
fig.savefig(f"{OUT}/fig_circuit_flow.pdf",bbox_inches="tight")
print("电路图实例 →",f"{OUT}/fig_circuit_flow.png")
