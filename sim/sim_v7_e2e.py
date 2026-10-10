"""R5 端到端模拟推理：6 层 MLP 经"电阻网络+BJT 读出+ADC"的精度损失
数字理想 (float64) vs 模拟链路（每层）：
  ① 电阻容差: R_j = R0/w_j · (1+δ), δ~N(0,tol)
  ② 求和热噪声: I_sum += N(0, sqrt(4kT·R_eq·BW)), 折算到输入端
  ③ BJT 读出增益 ±1% 失配
  ④ 8bit ADC + 层间归一化（模拟 CIM 标准做法）
指标：逐层余弦相似度 / 最终层相关 / top1 翻转率
"""
import numpy as np

kB, T, BW = 1.381e-23, 300, 1.6e6
VREF = 100e-3        # 输入摆幅 100mV（=1 单位）
R0 = 1e6
W_in = 512
layers_dims = [W_in, 1024, 1024, 1024, 512, 64]
L = len(layers_dims)-1
N_PAT = 300; N_MC_TOL = 40

rng_main = np.random.default_rng(42)
Ws = [rng_main.standard_normal((layers_dims[i+1], layers_dims[i]))*0.02
      for i in range(L)]
bs = [np.zeros(d) for d in layers_dims[1:]]

def relu(z): return np.maximum(z, 0)

def digital_layers(x):
    out=[x.copy()]
    for i in range(L):
        x = relu(x @ Ws[i].T + bs[i])
        out.append(x.copy())
    return out

def analog_layer(x, Wt, noise_sigma, gm):
    """单层：x (N,B0) -> z (N,B1)，含容差权重/热噪声/读出失配/8bit ADC
    noise_sigma: 已折算到 z 单位的热噪声 σ（调用方按 R_node 计算）"""
    B1 = Wt.shape[0]
    z = x @ Wt.T
    if noise_sigma > 0:
        z = z + rng_main.normal(0, noise_sigma, (x.shape[0], B1))
    z = z * (1 + gm)
    Vfull = max(np.abs(z).max(), 1e-9)
    step = 2*Vfull/256
    z = np.round(z/step)*step
    return relu(z)

print(f"R5 端到端 (L={L}, 输入维={W_in}, 总参数={sum(w.size for w in Ws):,}, R0={R0/1e6:.0f}MΩ)")
print("容差样本=40 (模拟 40 片不同芯片的器件失配)")
print("="*100)
print(f"{'容差':>6} | 最终层余弦 mean±std | top1 翻转率 | 说明")
print("-"*100)

for tol in [0.001, 0.01, 0.05, 0.10]:
    cos_all=[]; flips_all=[]
    Y_dig = digital_layers(X0 if (X0:=rng_main.random((N_PAT, W_in))) is not None else rng_main.random((N_PAT,W_in)))[-1]
    for mt in range(N_MC_TOL):
        Wt = [W*(1+rng_main.normal(0, tol, W.shape)) for W in Ws]
        gmis = [rng_main.normal(0, 0.01) for _ in range(L)]
        # 热噪声：折算到输入单位 (100mV=1)
        # σ_node = sqrt(4kT·R_eq·BW)，R_eq = R0/W_in_layer
        # 节点电流 I=x·G，折算回电压当量 σ_v = σ_node（电流×R0/W 量纲=V/100mV）
        Xd = rng_main.random((N_PAT, W_in))
        Yd = digital_layers(Xd)[-1]
        xa = Xd
        for i in range(L):
            # 热噪声：每个输出神经元一个求和节点，R_node = R0/Σ|w_j|（该神经元的 Σ|w|）
            Rnode = R0/np.abs(Ws[i]).sum(axis=1).mean()
            # 节点电流噪声 σ_I = sqrt(4kT·BW/R_node)；折算回 z 单位: ×R0/Vref
            nsg = np.sqrt(4*kB*T*BW/Rnode)*R0/VREF
            xa = analog_layer(xa, Wt[i], nsg, gmis[i])
        cos_all.append(np.einsum('ij,ij->', xa, Yd)/(np.linalg.norm(xa)*np.linalg.norm(Yd)))
        flips_all.append((np.argmax(Yd,1) != np.argmax(xa,1)).mean())
    cos_all=np.array(cos_all); flips_all=np.array(flips_all)
    tag = "INT8 可用" if cos_all.mean()>0.999 else ("边缘(建议 INT4/校准)" if cos_all.mean()>0.99 else "不可用(需校准/低精度)")
    print(f"{tol*100:5.2f}% | {cos_all.mean():.5f} ± {cos_all.std():.5f} | {flips_all.mean()*100:6.2f}% | {tag}")

# 逐层余弦（tol=1%, 噪声开）
print("\n逐层余弦相似度 (tol=1%, 热噪声开, 10 芯片样本平均):")
tol = 0.01
cos_stack = np.zeros((L, 10))
for mt in range(10):
    Wt = [W*(1+rng_main.normal(0, tol, W.shape)) for W in Ws]
    gmis = [rng_main.normal(0, 0.01) for _ in range(L)]
    Xd = rng_main.random((N_PAT, W_in))
    Yd_list = digital_layers(Xd)
    xa = Xd
    for i in range(L):
        Rnode = R0/np.abs(Ws[i]).sum(axis=1).mean()
        nsg = np.sqrt(4*kB*T*BW/Rnode)*R0/VREF
        xa = analog_layer(xa, Wt[i], nsg, gmis[i])
        c = np.einsum('ij,ij->', xa, Yd_list[i+1])/(np.linalg.norm(xa)*np.linalg.norm(Yd_list[i+1]))
        cos_stack[i, mt] = c
for i in range(L):
    m = cos_stack[i].mean()
    bar = "#"*int(m*50)
    print(f"  层{i+1}: {m:.5f} ± {cos_stack[i].std():.5f}  {bar}")
print("\n→ 误差逐层累积特征：若某层后余弦骤降，说明该层是精度瓶颈（通常是宽层）")
