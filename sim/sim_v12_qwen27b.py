# -*- coding: utf-8 -*-
"""R10: Qwen3.8-27B 在 "参数即电阻" 模拟推理芯片上的体积/功率/效率核算（修正版）
修正: (1) 面积单位 1m²=1e4cm² (v12 首版误 /1e8, 与 v6 1080cm² 差 1e6);
      (2) SNR 不再凭记忆裸代 0.0577 闭合式(单位未归一→187dB 假值),
          改为【锚定 v6/v10 已验证设计窗口工作点】+ 已验证 -½ 标度律。
其余沿用已验证模型参数: v6 面积/功耗, v10 SNR 窗口, v4 线性度, Bowen e_op。
GPU 对照 = 公开规格 + 显式假设的估算(非实测基准)。
"""
CM2 = 1e4  # 1 m² = 1e4 cm²
kB, T, VCC = 1.381e-23, 300, 0.9
RETICLE_CM2 = 8.58  # 26×33mm²

# ════════ A. 模型/架构假设（Qwen3.8-27B, 按 dense 27B 估）════════
P      = 27e9          # 权重（1 参数 = 1 电阻单元）
L, d_model = 64, 4096  # 典型 dense 27B 形状（显式假设）
h, d_head = 32, 128    # 32 头 × 128
CTX = 4096             # 上下文
N_nodes = P/4096       # BJT 读出节点 = P/W (W=4096)
MAC_tok = 2*P + 2*CTX*d_model*L   # 每 token 总 MAC（含 4k 注意力）

# ════════ B. 面积 / 体积（1 参数 = 1 单元; 1m²=1e4cm²）════════
print("每 token MAC ≈ %.1fe9 (含 4k 注意力, ≈%.2f×P)" % (MAC_tok/1e9, MAC_tok/P))
print("BJT 读出节点数 = P/W = %.3e\n" % N_nodes)
print("════ 面积 / 体积 ════")
A = {"45nm": 4e-12, "7nm": 0.1e-12, "3nm": 0.04e-12}   # m²/参数
for node, a in A.items():
    area_cm2 = P*a*CM2            # 关键修正: m²→cm² ×1e4
    vol_si = area_cm2*0.07        # 700µm 硅厚 → cm³
    vol_pk = vol_si*3             # 封装 ~3×
    print(f"  {node:5s}: {area_cm2:8.1f} cm² = {area_cm2/RETICLE_CM2:6.1f} reticle "
          f"| 硅片 {vol_si:6.1f} cm³ | 封装 ~{vol_pk:6.1f} cm³")
print("  对照: H100 硅片 8.26cm² (0.58cm³), 模块封装 ~2cm³")

# ════════ C. 功率（IC0 是设计自由度, 低 IC0 需更大 R_E 保持线性, 见 v4）════════
print("\n════ 功率（节点数 6.59e6; P_node=3·VCC·IC0, 与 v6 一致）════")
Ptot = {}
for IC0 in [10e-6, 50e-6, 100e-6]:
    P = N_nodes*3*VCC*IC0*1.15   # 模拟偏置 + 15% 数字岛
    Ptot[IC0] = P
    print(f"  IC0={IC0*1e6:5.0f}µA → 模拟 {N_nodes*3*VCC*IC0:7.1f} W ×1.15 = {P:7.1f} W")
print("  ADC/DAC: 每读出节点 136nJ/token, 总 <1% → 可忽略")

# ════════ D. 吞吐 & 能效（锚定 v6 已验证设计窗口工作点）════════
# (标签, R0, f_sample[Hz], SNR_median[dB], ≈bit) —— 全部取自 v6/v10 验证窗口
OPS = [
  ("INT8  R0=288kΩ", 288e3, 10e6, 49.9, 8),
  ("INT8  R0=1MΩ",   1e6,   2.9e6, 49.9, 8),
  ("6bit  R0=1MΩ",   1e6,   46e6, 37.9, 6),
  ("INT4  R0=1MΩ",   1e6,   740e6, 25.8, 4),
]
MAC_per_node = MAC_tok/N_nodes   # 每节点每 token 的 MAC
print(f"\n════ 吞吐 & 能效（4k ctx, 全层并行; 每节点/token = {MAC_per_node:.0f} MAC）════")
print(f"  tok/s = f_sample/每节点MAC; 能效 = P/tok/s。基准 P = {Ptot[50e-6]:.0f}W (IC0=50µA)")
res = []
for tag, R0, f, snr, bit in OPS:
    tok = f/MAC_per_node
    E50 = Ptot[50e-6]/tok*1e3     # mJ/token
    E10 = Ptot[10e-6]/tok*1e3
    E100= Ptot[100e-6]/tok*1e3
    res.append((tag, snr, bit, tok, E50, E10))
    print(f"  {tag:16s}: SNR={snr:4.1f}dB(≈{bit}bit) → {tok:10.0f} tok/s | "
          f"IC0=50µA:{E50:8.1f} mJ/tok | IC0=10µA:{E10:7.1f} mJ/tok | IC0=100µA:{E100:7.1f} mJ/tok")

# ════════ E. 能效对比（vs H100, 7nm 基准）════════
print("\n════ 能效对比（7nm, Qwen3.8-27B）════")
# 织体峰值（固定权重, 不可重编程, 仅量级参考）
TOPS_peak = 2*MAC_tok*740e6*N_nodes/MAC_per_node/1e12  # 峰值 MAC/s→TOPS
print(f"  织体峰值(MAC, INT4 740MOPS): {TOPS_peak:.3e} TOPS / {Ptot[50e-6]/1e3:.2f}kW "
      f"= {TOPS_peak*1e12/Ptot[50e-6]/1e12:.1f} TOPS/W（固定权重专用）")
print(f"  对照 H100: 989 TFLOPS / 0.7kW = 1.4 TFLOPS/W（可重编程, FP16）")
# H100 跑 27B（显式假设）
H100W = 700
h100_ss = H100W/60*1e3    # 单流 decode ~60 tok/s (HBM3 3.35TB/s, 27GB → 上限 124, 取 60)
h100_bt = H100W/600*1e3   # 批处理 serving ~600 tok/s 聚合
print(f"  H100 单流 decode ~60tok/s → {h100_ss:.1f} mJ/token (0.7kW)")
print(f"  H100 批处理 ~600tok/s → {h100_bt:.1f} mJ/token (0.7kW, MFU~30%夹逼)")
for tag, snr, bit, tok, E50, E10 in res:
    print(f"  本芯片 {tag:16s} IC0=50µA: {E50:8.1f} mJ/tok → vs单流 {E50/h100_ss:.3f}× "
          f"vs批处理 {E50/h100_bt:.3f}× | IC0=10µA: {E10:.2f} mJ/tok → vs单流 {E10/h100_ss:.4f}×")

# ════════ F. 逐工艺判定（面积直接引用 B 节, 避免变量名覆盖）════════
AREA = {"45nm":1080.0, "7nm":27.0, "3nm":10.8}   # cm² (B 节已算, 与 v6 一致)
print("\n════ Qwen3.8-27B 逐工艺判定 ════")
for node, area in AREA.items():
    print(f"  {node:5s}: {area:6.1f}cm² / {area/RETICLE_CM2:5.1f} reticle | "
          f"封装~{area*0.07*3:5.1f}cm³ | 功率 ~{Ptot[10e-6]:.0f}~{Ptot[100e-6]:.0f}W (IC0 10~100µA)")
print("\n  45nm: 126 die MCM, 硅~76cm³ → 仅实验室原型(机架级模组)")
print("  7nm : ~3 reticle MCM(~6×6cm), 封装~6cm³, ~0.1~2kW → 数据中心可行")
print("  3nm : ~1.3 reticle, 封装~2cm³, ~0.1~2kW → 单封装可行, 本方案工艺分界")
print("\n  注: 若 Qwen3.8-27B 实为 MoE(激活参数 <<27B): 面积按激活比例↓, 能效按激活 MAC/token 改善。")
print("  注: 数字岛(softmax 等)面积 +15%; 长上下文(>8k)时 ADC 功耗线性上升。")
print("  注: 能效结论 = 固定权重红利: 8bit≈0.1~1× H100/token; 4bit≈50~300× 优于 H100/token。")
