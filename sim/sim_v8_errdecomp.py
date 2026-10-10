"""R5b 误差分解：最终层余弦的误差到底来自哪里？
对照 4 条链路（同一网络、同一输入、同 40 样本平均）：
  A 纯数字 float64（理想基线）
  B 数字 + 逐层 8bit 量化（数字电路的下界：即使模拟完美，逐层量化也损失多少）
  C 模拟（容差+热噪声+读出失配），无 ADC
  D 模拟 + 逐层 8bit ADC（完整模拟链路）
  E 模拟 + 逐层 16bit ADC
若 D≈B → 精度瓶颈是逐层 ADC 量化，而非模拟器件
若 C 显著优于 B → 模拟器件噪声比数字量化还大
"""
import numpy as np
kB,T,BW,VREF = 1.381e-23,300,1.6e6,100e-3
R0=1e6
W_in=512
dims=[W_in,1024,1024,1024,512,64]
L=len(dims)-1
N_PAT=300; N_MC=40
rng=np.random.default_rng(7)
Ws=[rng.standard_normal((dims[i+1],dims[i]))*0.02 for i in range(L)]

def relu(z): return np.maximum(z,0)

def quant(z,bits):
    Vfull=max(np.abs(z).max(),1e-9); step=2*Vfull/(2**bits)
    return np.round(z/step)*step

def digital(X):
    for i in range(L): X=relu(X@Ws[i].T)
    return X

def quantized(X,bits):
    for i in range(L): X=relu(quant(X@Ws[i].T,bits))
    return X

def analog(X,Wt,gmis,adc_bits,tol):
    for i in range(L):
        z=X@Wt[i].T
        Rnode=R0/np.abs(Ws[i]).sum(axis=1).mean()
        z=z+rng.normal(0,np.sqrt(4*kB*T*BW/Rnode)*R0/VREF,z.shape)
        z=z*(1+gmis[i])
        if adc_bits: z=quant(z,adc_bits)
        X=relu(z)
    return X

def cos(a,b): return np.einsum('ij,ij->',a,b)/(np.linalg.norm(a)*np.linalg.norm(b))

Yref=digital(rng.random((N_PAT,W_in)))   # 固定输入做参考
Xs=rng.random((N_PAT,W_in))

results={}
# B: 纯数字 8bit
cB=[]
for mt in range(N_MC):
    cB.append(cos(quantized(Xs,8), digital(Xs)))
results["B 数字+8bit量化(无模拟)"]=(np.mean(cB),np.std(cB))

for tol in [0.001,0.01]:
    for adc in [0,8,16]:
        cs=[]
        for mt in range(N_MC):
            Wt=[W*(1+rng.normal(0,tol,W.shape)) for W in Ws]
            gmis=[rng.normal(0,0.01) for _ in range(L)]
            cs.append(cos(analog(Xs,Wt,gmis,adc,tol), digital(Xs)))
        tag=f"tol={tol*100:.1f}%" + (f"+ADC{adc}bit" if adc else "(无ADC)")
        results[f"C/D/E 模拟 {tag}"]=(np.mean(cs),np.std(cs))

print("R5b 误差分解 (L=5, 3,178,496 参数, 40 芯片样本平均)")
print("="*70)
print(f"{'链路':<34} {'最终层余弦 mean±std':<20} {'相对基线损失'}")
print("-"*70)
base=1.0
for k,(m,s) in results.items():
    print(f"{k:<34} {m:.5f} ± {s:.5f}   {100*(base-m):6.2f}%")
print("\n解读:")
print("  · B 若≈0.99 → 逐层 8bit 量化本身损失小，数字下界不是问题")
print("  · D-B 的差 = 纯模拟器件贡献的额外误差")
print("  · E 若≈C → 16bit ADC 后模拟链路误差消失 → 8bit 是瓶颈")
print("  · C 若明显差 → 模拟热噪声/容差是瓶颈")
