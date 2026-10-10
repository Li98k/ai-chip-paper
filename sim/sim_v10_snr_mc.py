"""R5d SNR 严格 Monte-Carlo（不再用解析近似）
直接构造 crossbar 求和节点：
  W 个支路，支路 j: 电阻 R_j=R0/w_j，电导 G_j=w_j/R0
  输入 x_j~U(0,1)，信号电流 I_sig = Σ x_j·G_j（虚拟地求和）
  每支路热噪声电流 σ_j = sqrt(4kT·BW·G_j)，独立
  节点总噪声 = sqrt(Σ σ_j²)（虚地点并联，功率相加）
  SNR = |I_sig| / I_noise   （对一批随机输入取统计）
扫描 W × R0 × BW(吞吐)，给出标度律 + 有效位数。
这是整篇论文可行性的定量命门，必须算准。
"""
import numpy as np
kB,T = 1.381e-23,300.0
VREF=100e-3   # 输入满幅 100mV
R0=1e6
rng=np.random.default_rng(0)
N_BATCH=4000  # 输入批次数

def snr_mc(W, R0, BW, ntrials=200):
    """返回 (SNR_lin数组, I_sig均值, I_noise)"""
    snrs=[]
    sigs=[]; noises=[]
    for t in range(ntrials):
        w = rng.standard_normal(W)          # 权重 ~N(0,1)（含正负）
        G = w/R0                             # 电导，可正可负（差分实现）
        x = rng.random(W)*VREF               # 输入 0~100mV
        I_sig = np.sum(x*G)                  # 求和电流
        I_noise = np.sqrt(np.sum(4*kB*T*BW*np.abs(G)))  # 噪声电流（用|G|）
        sigs.append(abs(I_sig)); noises.append(I_noise)
        if abs(I_sig)>1e-30:
            snrs.append(abs(I_sig)/I_noise)
    snrs=np.array(snrs)
    return snrs, np.mean(sigs), np.mean(noises)

print("R5d 严格 Monte-Carlo SNR（crossbar 虚地点, 每支路热噪声, |G|）")
print("I_sig=Σ x·G, I_noise=√(Σ 4kT·BW·|G_j|), SNR=I_sig/I_noise")
print("="*96)

# 标度 1: 固定 R0, BW，扫 W → 看 SNR ∝ W^?
print("\n[标度1] SNR vs 层宽 W (R0=1MΩ, 10MOPS→BW=5MHz):")
BW=5e6
base=None
for W in [256,512,1024,2048,4096,8192,16384]:
    snrs,sig,noise=snr_mc(W,R0,BW)
    db=20*np.log10(np.median(snrs))
    if base is None: base=(W,db)
    ratio=(db-base[1])/ (10*np.log10(W/base[0]))
    print(f"  W={W:6d}: SNR={db:6.1f} dB  (≈{(db-1.76)/6.02:4.1f} bit)  "
          f"标度指数 dSNR/dlogW={ratio:4.2f}")

# 标度 2: 固定 W, BW，扫 R0 → SNR ∝ R0^?
print("\n[标度2] SNR vs R0 (W=4096, BW=5MHz):")
W=4096; BW=5e6
base=None
for R0x in [1e5,5e5,1e6,5e6,1e7]:
    snrs,sig,noise=snr_mc(W,R0x,BW)
    db=20*np.log10(np.median(snrs))
    if base is None: base=(R0x,db)
    ratio=(db-base[1])/(10*np.log10(R0x/base[0]))
    print(f"  R0={R0x/1e6:5.2f}MΩ: SNR={db:6.1f} dB  标度指数 dSNR/dlogR0={ratio:5.2f}")

# 标度 3: 固定 W, R0，扫 BW(吞吐)
print("\n[标度3] SNR vs 吞吐 (W=4096, R0=1MΩ):")
W=4096; R0x=1e6
base=None
for name,ops in [("1GOPS",1e9),("100MOPS",1e8),("10MOPS",1e7),("1MOPS",1e6),("100kOPS",1e5)]:
    BW=ops/2
    snrs,sig,noise=snr_mc(W,R0x,BW)
    db=20*np.log10(np.median(snrs))
    if base is None: base=(BW,db)
    ratio=(db-base[1])/(10*np.log10(BW/base[0]))
    print(f"  {name:8s}(BW={BW/1e6:6.1f}MHz): SNR={db:6.1f} dB (≈{(db-1.76)/6.02:4.1f}bit)  标度={ratio:5.2f}")

print("\n[判读] 对照 INT8=48.2dB / INT4=24.8dB 门槛，给出可行的 (W,吞吐) 区域")
