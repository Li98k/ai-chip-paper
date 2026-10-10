"""R4 设计空间全扫描（crossbar 单元模型，修正版）
物理模型（电流模虚拟地 crossbar，用户方案的正确实现）：
  每个权重 = 1 个存储单元（R_11/w，1T1R / 1T1R），单元面积 A_cell
  单元电导 G_11=w/R0；R0 决定"单元可实现的电导范围"
  节点 = W 个单元并联求和（虚拟地）+ BJT 电流镜读出
三层判据（INT8）：
  ① 热噪声 SNR ≥ 48.2 dB   SNR = VREF·sqrt(Σ|w|/(4kT·BW·R0))  [电流模]
  ② 建立 τ = R_eq·C_node ≤ 20 ps   R_eq=R0/Σ|w|
  ③ 单元面积 A_node = W·A_cell + A_out  ≤ A_budget/节点
  ④ 直流 P_node = 2·VCC·IC0 + P_drv ≤ P_budget
真正的系统级约束是 ③ 面积（R0 通过 A_cell 进入）与容差（精度）。
"""
import numpy as np
kB,T,VCC = 1.381e-23,300,0.9
VREF=100e-3; BW=1.6e6; C_node=5e-15
A_cell=4e-12        # 45nm 1T1R 单元 4µm² (256nm×16 行 或 1µm² 保守取 4)
A_out =1e-12        # 读出管 ~1µm²
W=4096
print("R4 设计空间 (W=%d, A_cell=%gµm², C_node=%gfF)"%(W,A_cell*1e12,C_node*1e15))
print("单元模型: 每个权重=1 存储单元; R0 决定单元电导范围; Σ|w|≈W")
print("="*108)

# 热噪声 SNR（R7 最终闭合式, 与 v10 严格 MC median 差 <1dB）
# SNR_RMS = VREF/√(3·4·√(2/π)·kT·BW·R0) = 0.0577/√(3.1916·kT·BW·R0)
#   信号 std = VREF·√(W/3)/R0 (E[x²]=V²/3);  噪声 = √(4kT·BW·W·√(2/π)/R0)
#   → W 精确抵消；MC median = RMS − 3.4dB（|I_sig| 半正态中位效应）
print("\n① 热噪声 SNR（电流模, R7 闭合式 = v10 MC 验证）:")
R0=1e6
for name, T_step in [("100MOPS",10e-9),("10MOPS",100e-9),("1MOPS",1e-6),("100kOPS",10e-6)]:
    BWx=1/(2*T_step)
    snr_r=20*np.log10(0.0577/np.sqrt(3.1916*kB*T*BWx*R0))
    snr_med=snr_r-3.4
    snr_r100k=snr_r+20*np.log10(np.sqrt(R0/1e5))
    print(f"   {name:8s}(BW={BWx/1e6:7.2f}MHz): R0=1MΩ → RMS {snr_r:5.1f}dB / median {snr_med:5.1f}dB"
          f"(≈{(snr_med-1.76)/6.02:.1f}bit) | R0=100kΩ → median {snr_r100k-3.4:5.1f}dB(≈{(snr_r100k-3.4-1.76)/6.02:.1f}bit)")
print("   标度律（MC 实测指数）: SNR vs W ≈0（无关）; vs R0 ≈ -½; vs 吞吐 ≈ -½")
print("   → INT8(median 49.9dB) 窗口: R0≤29kΩ@100MOPS | R0≤288kΩ@10MOPS | R0=1MΩ@≤2.9MOPS")
print("   → 6bit(median 37.9dB): R0=1MΩ@≤46MOPS | INT4(median 25.8dB): R0=1MΩ@≤740MOPS")
print("   → 缓解: 降吞吐/小 R0/过采样降有效带宽/INT4 降级/多 token 平均")

# 建立时间
print("\n② 建立时间 τ=R_eq·C (R_eq=R0/W):")
for R0 in [100e3,1e6,10e6]:
    tau=R0/W*C_node*1e12
    print(f"   R0={R0/1e3:6.0f}kΩ → τ={tau:6.2f} ps  (≤20ps 满足 100MOPS 窗 2%)")
print("   → W=4096 时 τ 全部 <15ps → 速度非约束项（大 W 摊薄 R_eq）")

# 面积（系统级约束）——单位统一用 µm²
print("\n③ 面积（真正约束项, A_node=W·A_cell+A_out）:")
A_node_u2 = W*A_cell*1e12 + A_out*1e12   # µm²
print(f"   单节点面积 = {W}×{A_cell*1e12}µm²+{A_out*1e12}µm² = {A_node_u2:.0f} µm²")
for die_mm2 in [100,500,1000]:
    die_u2 = die_mm2*1e6                 # mm²→µm²
    n_node = die_u2/A_node_u2
    n_param = n_node*W                   # 每节点 W 个参数
    print(f"   die={die_mm2:4d}mm² → {n_node:8.0f} 节点 = {n_param/1e6:7.1f}M 参数")

# 2.5B / 27B 需要的硅面积
print("\n   → 容纳目标参数量所需硅面积 (45nm, 1T1R 4µm²):")
for P_target in [2.5e9, 7e9, 27e9]:
    n_node = P_target/W
    area_mm2 = n_node*A_node_u2/1e6
    print(f"      {P_target/1e9:4.1f}B 参数 → {n_node:.3e} 节点 → {area_mm2:8.0f} mm² = {area_mm2/100:6.1f} cm²"
          f"   ({area_mm2/1000:4.1f} 个 100mm² die)")

# 直流功耗
print("\n④ 直流功耗 P_node=2·VCC·IC0+P_drv (P_drv≈VCC·I_drv, I_drv~IC0):")
for IC0 in [10e-6,50e-6,100e-6,500e-6]:
    P=2*VCC*IC0+VCC*IC0   # 尾电流×2 + 驱动
    print(f"   IC0={IC0*1e6:5.0f}µA → P_node={P*1e6:5.1f}µW  (单节点)")
print("   → 2.5B 参数 @ IC0=50µA: 总直流 =", f"{2.5e9/W*3*VCC*50e-6:.0f}W")
print("     2.5B @ IC0=10µA: 总直流 =", f"{2.5e9/W*3*VCC*10e-6:.0f}W")

# 容差→精度（引 v5b C5 结论）
print("\n⑤ 容差→精度（INT8 判据, 来自 C5 Monte Carlo）:")
for tol,mean,p95 in [(0.001,0.001,0.002),(0.01,0.009,0.021),(0.05,0.044,0.105),(0.10,0.090,0.210)]:
    ok="INT8✓" if mean<0.00195 else ("INT6" if mean<0.0078 else "需校准/低精度")
    print(f"   容差 {tol*100:5.2f}%: 输出误差 mean={mean*100:5.2f}% p95={p95*100:5.2f}% → {ok}")

print("\n"+"="*108)
print("★ 设计空间结论（R6 最终版）：")
print("  · 【硬约束 1 = 面积】1 参数 = 1 存储单元（1cm² ≈ 1 个 100mm² die ≈ 12% reticle）：")
print("    45nm: 2.5B=100cm²(100 die), 7B=280cm², 27B=1080cm²(≈126 reticle) → 必须多芯片/MCM")
print("  · 7nm: 27B=27cm² | 3nm: 27B=10.9cm² ≈ 1.3 reticle → 先进节点下大模型单/少 die 可行")
print("  · 【硬约束 2 = 噪声/吞吐】随机输入 SNR 与 W 无关，∝R0^-½, ∝吞吐^-½：")
print("    10MOPS/R0=1MΩ≈6.5bit; 1MOPS≈8.2bit; 10MOPS/R0=100kΩ≈8.2bit → INT8 窗口明确")
print("  · 精度第三来源 = 单元容差：0.1% 单元→INT8；1% 单元→INT4 或失配感知训练")
print("  · 速度：大 W 下 τ<15ps，非约束项")
print("  · 直流功耗：IC0=50µA 时 2.5B≈82W（10µA→16W, 100µA→164W, 27B@100µA≈1.78kW）")

# 27B 外推（先进节点对比）
print("\n27B 规模外推（面积主导）:")
for tag, a_cell in [("45nm 4µm²",4e-12),("7nm 0.1µm²",0.1e-12),("3nm 0.04µm²",0.04e-12)]:
    An_u2 = W*a_cell*1e12 + A_out*1e12
    n_node = 27e9/W
    area_mm2 = n_node*An_u2/1e6
    ndies100 = area_mm2/100
    P_dc = n_node*3*VCC*100e-6
    feas = "单 die 可行" if area_mm2<100 else f"{ndies100:.0f} 个 100mm² die"
    print(f"  {tag:12s}: 27B → {area_mm2:8.0f} mm² = {area_mm2/100:7.1f} cm²  [{feas}]  直流(100µA)={P_dc:.0f}W")
