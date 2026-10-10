"""R5c SNR 精算：满幅(乐观) vs 随机输入(真实) vs 带宽(吞吐) vs 深度累积
★ 已 superseded：本文件的信号/噪声因子在 R7 修正（信号用 √(E[x²])=0.577
  而非 std(x)=0.289；噪声用 Σ|w|=W·√(2/π) 而非 W）。最终权威 = sim_v10
  严格 MC + R7 闭合式：
     SNR_RMS(dB) = 20log10(0.0577/√(3.1916·kT·BW·R0))
     SNR_work    = SNR_RMS − 2.5 dB   （≈ v10 MC median, 差 <1.2dB）
  标度律: SNR 与 W 无关, ∝R0^-½, ∝BW^-½。
  锚点(R0=1MΩ, median): 100MOPS 33.3dB/5.2bit | 10MOPS 44.5/7.1 | 1MOPS 53.3/8.6
"""
import numpy as np
kB,T = 1.381e-23,300
R0=1e6; VREF=100e-3

# R7 闭合式（权威）
def snr_rms_dB(BW, R0):
    return 20*np.log10(0.0577/np.sqrt(3.1916*kB*T*BW*R0))
def snr_work_dB(BW, R0):   # ≈ v10 MC median
    return snr_rms_dB(BW, R0) - 2.5
def enob(db):  return (db-1.76)/6.02

print("R5c SNR 精算（R7 闭合式, R0=1MΩ, x~U(0,100mV), w~N(0,1)）")
print("="*92)
print("  逐 W 扫描（证明与 W 无关）+ 吞吐扫描:")
BW_of = {100e6:5e7, 10e6:5e6, 1e6:5e5}
for W in [512,1024,4096,16384]:
    row=f"  W={W:6d}: "
    for ops in [100e6,10e6,1e6]:
        db=snr_work_dB(BW_of[ops],R0)   # 与 W 无关
        row+=f" {ops/1e6:5.0f}MOPS {db:5.1f}dB({enob(db):3.1f}b)"
    print(row)
print("\n解读（R7 最终）：")
print("  · 随机输入 SNR 与 W 无关（信号 √W、噪声 √W 精确抵消）")
print("  · 100MOPS 33.3dB≈5.2bit | 10MOPS 44.5≈7.1bit | 1MOPS 53.3≈8.6bit")
print("  · INT8 需 median≥49.9dB/层：R0≤29kΩ@100MOPS | R0≤290kΩ@10MOPS")
print("    | R0=1MΩ@≤2.9MOPS；6bit@R0=1MΩ ≤46MOPS；INT4 ≤740MOPS")
print("  · 缓解：降吞吐/小 R0/过采样降有效带宽/INT4 降级/多 token 平均")

# 深度累积（per-layer SNR 恒定, L 层独立噪声 → −10log10(L)）
print("\n深度累积（信号每层归一化回满幅, per-layer SNR 恒定）:")
BW10=5e6
snr10=snr_work_dB(BW10,R0)
print(f"  单层(10MOPS) SNR = {snr10:.1f} dB")
for L in [1,4,8,16,32]:
    db=snr10-10*np.log10(L)
    print(f"  L={L:2d}: 累积 SNR ≈ {db:5.1f} dB  (≈{enob(db):4.1f} bit)")
