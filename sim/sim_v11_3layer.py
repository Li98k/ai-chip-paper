"""R8: 三层网络 "参数即电阻" 布线数值验证
3→2→2 全连接，逐层 crossbar（虚拟地）+ BJT 读出。
核心命题：三级电阻布线 精确 实现 z = W2·(W1·x)，
即把矩阵乘法写进欧姆定律，无需读-乘-写的数据搬运。
同时给出每条连线的真实电阻值 R=R0/w，以及负权重（差分对）的处理。
"""
import numpy as np

R0 = 1e6          # 归一化基准电阻 (Ω)

# ---- 权重（含负值，真实 LLM 情形）----
# 约定 W[out][in]：W[j][i]=从输入 i 到输出 j 的权重
W1 = np.array([[ 0.8,  0.3, -0.2],   # L1(3)->L2 输出1
               [-0.5,  0.7,  0.4]])   #            ->L2 输出2
W2 = np.array([[ 0.6, -0.4],         # L2(2)->L3 输出1
               [ 0.9,  0.2]])         #            ->L3 输出2
x = np.array([0.080, 0.040, 0.060])  # L1 激活 (V), 0~100mV

print("="*78)
print("三层 '参数即电阻' 布线数值验证   (3→2→2, R0=1MΩ)")
print("="*78)

def show_wiring(tag, W, x_in):
    print(f"\n[{tag}]  输入 = {np.round(x_in*1000,1).tolist()} mV")
    print("  连线电阻 R=R0/w（负权重→差分对, 下表列 |R| 与符号）:")
    for j in range(W.shape[0]):           # 每个输出节点
        col=[]
        for i in range(W.shape[1]):       # 每条汇入连线
            w=W[j,i]; R=R0/abs(w); sign="+" if w>=0 else "−"
            col.append(f"{sign}{R/1e3:6.1f}kΩ←x{i+1}")
        print(f"    节点{j+1}:  " + "  ".join(col))

# 理想虚拟地：节点电流 I_j=(1/R0)·Σ_i w_ij·x_i   [A]
I2 = (W1 @ x)/R0        # L2 两节点电流
R_L = R0                # BJT 读出负载，取 R_L=R0
y2 = I2*R_L             # = W1@x  (V)
I3 = (W2 @ y2)/R0       # L3 两节点电流
z3 = I3*R_L             # = W2@y2 (V)
z_dig = W2 @ (W1 @ x)   # 数字参考

show_wiring("第1级 布线 L1→L2 (3输入×2节点)", W1, x)
show_wiring("第2级 布线 L2→L3 (2输入×2节点)", W2, np.round(y2*1000,2)/1000)

print("\n节点电流 / 读出（模拟布线结果）:")
print(f"  L2: I=[{I2[0]*1e9:6.2f}, {I2[1]*1e9:6.2f}] nA   y=[{y2[0]*1000:5.1f}, {y2[1]*1000:5.1f}] mV")
print(f"  L3: I=[{I3[0]*1e9:6.2f}, {I3[1]*1e9:6.2f}] nA   z=[{z3[0]*1000:5.1f}, {z3[1]*1000:5.1f}] mV")
print(f"  数字参考: z_dig = [{z_dig[0]*1000:5.1f}, {z_dig[1]*1000:5.1f}] mV")
err=np.max(np.abs(z3-z_dig))/np.max(np.abs(z_dig))
print(f"  最大相对误差 = {err:.2e}   (纯代数恒等, 仅浮点误差)")

# 等效电导视角（用户原话："多条连线汇入→阻值变化→电流变化"）
print("\n等效电导视角（多线汇入一节点）:")
for j in range(W1.shape[0]):
    G = W1[j,:].dot(x)/R0   # = I_node
    print(f"  L2节点{j+1}: I=(1/R0)·Σ w_i·x_i = {G*1e9:6.2f} nA")
print("  → 等效电导 G_node=(1/R0)·Σ w_i·x_i 随输入加权变化")
print("    → 节点电流随之变化 —— 用户原话的物理实现（欧姆定律）")

# BJT 读出线性度（R_E 负反馈）
print("\nBJT 读出线性度（R_E 负反馈, 工作点 IC0=200µA, VT=25.85mV）:")
VT=25.85e-3; IC0=200e-6; g_m=IC0/VT
for R_E in [1e3,2e3,2.6e3]:
    A=1/(R_E+1/g_m)
    print(f"   R_E={R_E/1e3:4.1f}kΩ → 局部跨导≈{A*1e3:5.2f} mS (被 R_E 线性化, 与 β 无关)")
print("   → 0~100mV 全摆幅非线性 <0.2%（详见 sim_v4）")

print("\n★ 三层布线原理结论:")
print("  z = W2·(W1·x)  由 3 级 crossbar 级联 精确 完成")
print("  每一级: 布线电阻 R=R0/w 存参数 → 虚拟地欧姆求和 → BJT 读出")
print("  数据搬运(读-乘-写)被欧姆定律取代; 层间只传模拟电压/电流。")
