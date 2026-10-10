# -*- coding: utf-8 -*-
"""R11: 发热影响 + 立体(3D)堆叠体积 + 器件/材料替代 核算
输入: sim_v12 的 27B 功耗/面积(7nm 27cm², IC0 10/50/100µA → 0.2/1.0/2.0kW)
     BJT 物理: IS 每 +7°C 翻倍, VBE -2mV/°C, α(TC)~-0.1%/°C
     噪声: SNR ∝ 1/√T (v10/v6)
"""
import numpy as np

print("════ A. 功率密度与结温（Qwen3.8-27B, 7nm 27cm² / 3nm 10.8cm²）════")
P_kW = {10e-6: 0.205, 50e-6: 1.02, 100e-6: 2.05}
A7, A3 = 27.0, 10.8
for name, A in [("7nm", A7), ("3nm", A3)]:
    print(f"  {name} ({A:.1f}cm²): " + " | ".join(
        f"IC0={k*1e6:.0f}µA→{v*1e3/A:.0f}W/cm²" for k, v in P_kW.items()))
print("  对照 H100: 700W/8.26cm² = 85 W/cm²")

# 结温: ΔT = (P/A)×θ_area; 液冷冷板 θ_area≈0.1 K·cm²/W;
#       风冷用 H100 实测校准: 85W/cm², Ta=45→Tj≈105°C → θ_area≈0.6 K·cm²/W
print("\n  结温估计(环境 25°C, 加 die-到-散热器 ~5K):")
for kind, th in [("液冷(冷板 0.1 K·cm²/W)", 0.1), ("风冷(H100 校准 0.6 K·cm²/W)", 0.6)]:
    rows = []
    for k, v in P_kW.items():
        q = v*1e3/A7            # W/cm² @7nm
        Tj = 25 + 5 + q*th
        rows.append(f"{k*1e6:.0f}µA→Tj≈{Tj:.0f}°C")
    print(f"   {kind} [7nm 27cm²]: " + " | ".join(rows))
    rows = []
    for k, v in P_kW.items():
        q = v*1e3/A3
        Tj = 25 + 5 + q*th
        rows.append(f"{k*1e6:.0f}µA→Tj≈{Tj:.0f}°C")
    print(f"   {kind} [3nm 10.8cm²]: " + " | ".join(rows))
print("   → 液冷: 3nm 也全部 <55°C; 风冷: 7nm 可(≤77°C), 3nm@100µA 爆(>150°C)必须液冷")

print("\n════ B. 温度对性能的影响（逐项量化）════")
print("  ① 热噪声: SNR∝1/√T (v6 闭合式) → 25°C→105°C: %+.1fdB; →125°C: %+.1fdB (对 12dB 裕量可忽略)"
      % (10*np.log10(298/378), 10*np.log10(298/398)))
# BJT 漏流 IS 每 7°C 翻倍
for Tj in [45, 65, 85, 105]:
    fac = 2**((Tj-25)/7)
    print(f"  ② BJT 漏流 IS(Tj={Tj}°C) = 25°C 的 {fac:8.0f}×  "
          f"({'致命: 超过偏置电流→热失控' if fac>200 else '需温度补偿' if fac>20 else '可接受'})")
print("  ③ VBE 漂移 -2mV/°C: ΔT=75K → -150mV 偏置/失调 → 需一次性校准或带隙基准(可解)")
print("  ④ α(TC)≈-0.1%/°C: ΔT=75K → -7.5% 增益 → 对模拟求和只是整体缩放, 被读出增益吸收(可忽略)")
# 电阻温漂: 共模抵消论证
a_spread = 20e-6  # 同批薄膜 α 离散 ~20ppm
dR = a_spread*75*100
print(f"  ⑤ 权重电阻温漂: R_j 与 R0 同材料同批 → 共模漂移在 I=(1/R0)Σw·x 中【精确抵消】;")
print(f"     剩余 = 差模 α 离散 ~20ppm×75K = {dR:.2f}% → 叠加 0.1% 单元容差仍 ≈INT8 边缘(可校准)")

print("\n════ C. 立体(3D)堆叠: 体积 / TSV / 层间温升（7nm 27cm²）════")
print("  硅体积固定(=27B 单元数不变), 3D 缩的是【占位面积 footprint】, 代价=TSV/hybrid bonding:")
# 2D MCM: 3 reticle 并排 (1×3), die=2.6×0.99cm
foot2d = 2.6*3.3*3   # cm²  (1 reticle 8.58cm² × 3 并排 = 25.74 cm²)
h2d = 0.2              # cm (基板+塑封)
vol2d = foot2d*h2d
# 3D: 4 片堆叠, 每片 27/4=6.75cm² < 1 reticle(8.58)
S7 = 4
foot = 27/S7
h_mm = 0.7*S7 + 0.6    # 硅厚 4×0.7mm + TSV/中介层 0.6mm = 3.4mm
h3 = h_mm/10
vol3d = foot*h3
print(f"  2D MCM(3 reticle 并排): 占位 {foot2d:.1f}cm² × 高 {h2d*10:.1f}mm = {vol2d:.1f} cm³")
print(f"  3D {S7} 片堆叠:        占位 {foot:.2f}cm²(单 reticle 内) × 高 {h_mm:.1f}mm = {vol3d:.1f} cm³ "
      f"→ 占位 {foot2d/foot:.1f}×↓, 体积 {vol2d/vol3d:.1f}×↓")
foot3 = 10.8; h3n = 0.7*2+0.5   # 3nm 2D 已是 ~1.3 reticle
print(f"  3nm(2D 已 ~1 reticle): 占位 ~10.8cm² × 高 1.9mm ≈ {10.8*0.19:.1f} cm³ → 3D 边际收益小")
# 层间 TSV: 每神经元过 1 个层间接口, 4 层 → 每接口 N/4 根
N_nodes = 27e9/4096
tsv = N_nodes/S7
area_int = foot*1e8       # cm²→µm² (1cm²=1e8µm²)
pitch = np.sqrt(area_int/tsv)
print(f"  层间互连: 每接口 {tsv/1e6:.2f}M 根 TSV @ {foot:.2f}cm² → pitch ≈ {pitch:.0f}µm")
print("    → ~20µm pitch: 比标准 flip-chip µbump(40-55µm)更密, 需细间距 µbump 或 hybrid bonding;")
print("      (若每界只传 d=4096 隐藏态而非全节点, TSV 数大降, pitch 放宽——取决于层切分方式)")
# 3D 下层温升 (IC0=100µA, 2kW, 4 层)
Ptot = 2000
r_stack = 0.1  # K·cm²/W per interface (硅+TSV 热阻)
dT_bottom = (S7-1)*(Ptot/S7)*r_stack/foot
print(f"  3D 热: 底层 die 额外温升 ≈ (S-1)×(P/S)×0.1/{foot:.1f} = +{dT_bottom:.0f}K (IC0=100µA)")
print("    液冷下底层 Tj≈35+22≈57°C → BJT IS×2^(32/7)≈33× → 仍需温度补偿, 但可解")


print("\n════ D. 器件替代（定性, 按先进节点可得性排序）════")
print("""  读出放大(替代 BJT):
   MOSFET(CMOS 电流镜/sense-amp)  纯 CMOS 可造(7/3nm 主流), 1/f 噪声角~10-100kHz(10MHz 读出时
                                   可忽略), 亚阈值漏电 TC 温和 → 【7/3nm 下的实际选择】
   BJT(BiCMOS)                    1/f 低(~100Hz), fT 高, VBE 摆幅小; 但 BiCMOS 仅到 ~28/14nm
                                   → 45nm 原型优选, 先进节点不可得
   二极管/Schottky                I∝e^{V/VT} 对数特性 → 不是线性读出, 但【天然实现 softmax 的
                                   exp】: 注意力层可用二极管做模拟 softmax(红利, 非替代)
   JFET/MESFET                    高阻/低噪, 与 CMOS 不兼容, 仅研究
   纳米线 FET / MoS2 2D-FET       研究阶段, 离散性大, 远期
  权重电阻(替代/补充):
   NiCr/TaN 薄膜 + 激光修阻       ±25-50ppm/°C, 噪声低, 一次性 trim → 固定权重首选
   ReRAM(HfOx)/PCM                非易失(断电权重不丢), 但离散 3-10% → 精度掉到 INT4 或需校准
   浮栅/flash                      非易失, 离散大, 同上
  → 组合结论: 7/3nm = MOS 读出 + NiCr/TaN 薄膜电阻(标准 CMOS 可造); 45nm 原型 = BJT+薄膜
""")
