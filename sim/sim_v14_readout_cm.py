# -*- coding: utf-8 -*-
"""R12: 读出级控制模态验证 —— BJT(电流控制) vs MOS(电压控制) vs 更优方案
核心: crossbar 虚拟地输出的是【电流和】I_sig。
  BJT 控制量 = 基极电流 I_B(电流)  → 与 crossbar 输出(电流)【本征匹配】, 无需阻抗转换
  MOS 控制量 = 栅压 V_GS(电压)     → 与 crossbar 输出(电流)【模态失配】, 必须 I→V 转换
锚定 INT8@10MOPS: R0=288kΩ, 奈奎斯特 BW=5MHz; I_sig/I_noise 用 v6/v10 已验证公式。
单位: A→nA ×1e9。
"""
import numpy as np
kB, T, q, VREF = 1.381e-23, 300, 1.602e-19, 100e-3
W, R0, BW = 4096, 288e3, 5e6
nA = lambda a: a*1e9

I_sig   = VREF*np.sqrt(W/3)/R0          # 12.83 µA
I_noise = np.sqrt(4*kB*T*BW*W/R0)       # crossbar 热噪声基底 (v6/v10)
snr0 = 20*np.log10(I_sig/I_noise)
print("════ 控制模态验证（锚定 INT8@10MOPS: R0=288kΩ, BW=5MHz）════")
print(f"  crossbar 输出(电流和): I_sig={I_sig*1e6:.1f}µA(RMS); 噪声基底 I_noise={nA(I_noise):.1f}nA")
print(f"  基底 SNR={snr0:.1f}dB(RMS)≈{(snr0-1.76)/6.02:.1f}bit; 本方案有效 SNR 以 v10/v6 设计窗口为准")
print(f"  （读出噪声与基底同量级时必须计入, 下表给出 R_E/R_f 的设计扫描）\n")

def add_snr(n_add):
    n_tot = np.sqrt(I_noise**2 + n_add**2)
    return 20*np.log10(I_sig/n_tot)

print("────────── 方案 A: BJT 电流镜读出（发射极退化, 电流控制）──────────")
beta = 100
I_base = I_sig/beta
n_shot = np.sqrt(2*q*I_sig*BW)
print(f"  本征匹配: crossbar 电流直驱基极, 无需阻抗转换; 1/f 角低(~100Hz)")
print(f"  代价① DC 输入负载 = I_sig/β = {nA(I_base):.2f}nA = {100/beta:.1f}% of I_sig (抽走 crossbar 电流)")
print(f"  代价② 附加噪声(散粒 {nA(n_shot):.1f}nA + R_E 热): R_E 是设计自由度(大 R_E→更线性但 R_E 热噪声↑)")
print(f"    {'R_E':>6} {'n_RE':>8} {'n_total':>9} {'SNR(含读出)':>13} {'惩罚':>7}")
for RE in [50, 100, 280, 1000]:
    n_re = np.sqrt(4*kB*T*BW/RE)
    n_tot = np.sqrt(n_shot**2 + n_re**2)
    s = add_snr(n_tot)
    print(f"    {RE:>6}Ω {nA(n_re):>7.1f}n {nA(n_tot):>8.1f}n {s:>10.1f}dB {s-snr0:>+6.1f}dB")
print(f"  线性度: I_out=(W2/W1)·I_sig【线性】; 增益精度 镜比±1-2% (+1/β~1%)")
print(f"  节点: BiCMOS 仅 ≤28/14nm → 7/3nm【不可得】\n")

print("────────── 方案 B: MOS 读出（电压控制）──────────")
print("  B1 朴素单 MOS(直接平方律): I_D∝(V_GS-Vth)² → 2nd 谐波【非线性】; 需 I_sig·R_load>V_th")
gm = 2e-4
print(f"  B2 MOS 跨阻 TIA: 栅【绝缘, 0 DC 负载】(不抽 crossbar 电流); 增益管维持虚地→V_out∝I_sig【线性】")
print(f"    附加噪声 = R_f 热 + MOS 沟道; R_f 是设计自由度(大 R_f→噪声↓, 但摆幅↑):")
print(f"    {'R_f':>7} {'n_Rf':>8} {'n_tot':>9} {'SNR(含读出)':>13} {'惩罚':>7}")
for Rf in [1e3, 2.88e4, 1e5]:
    n_rf = np.sqrt(4*kB*T*BW/Rf)
    n_ch = np.sqrt(4/3*kB*T*gm*BW)      # MOS 沟道热噪声(折输入电流, 代表)
    n_tot = np.sqrt(n_rf**2 + n_ch**2)
    s = add_snr(n_tot)
    print(f"    {Rf/1e3:>6.1f}k {nA(n_rf):>7.1f}n {nA(n_tot):>8.1f}n {s:>10.1f}dB {s-snr0:>+6.1f}dB")
print(f"  增益精度: R_f ±1-2%; 节点: 纯 CMOS, 7/3nm【可得】→ 先进节点唯一选择\n")

print("════ 控制模态对比（关键: 模态匹配度）════")
print("  指标            BJT(电流控制)        MOS TIA(电压控制)")
print("  crossbar 输出     电流和               电流和")
print("  控制量            I_B(电流)=本征匹配    V_GS(电压)=模态失配")
print("  阻抗转换          无(电流直驱基极)      必须 I→V(R_f, 加热噪声)")
print(f"  DC 输入负载       I_sig/β≈{100/beta:.0f}%             0(栅绝缘)")
print(f"  读出噪声@10MOPS  R_E=50Ω→41nA(≈-4dB)   R_f=28.8k→3nA(≈0dB, 可忽略)")
print("  1/f 角            ~100Hz(低)           ~50kHz(高, 10MHz 读出可忽略)")
print("  7/3nm 可得        否(BiCMOS 断供)       是(纯 CMOS)")
print("  结论: 控制模态差异 → ①MOS 需 I→V(R_f 热噪声) ②BJT 抽 I_sig/β 负载 ③BJT 先进节点断供")
print("        噪声上: BJT(R_E~50Ω)读出与基底相当(≈-4dB), MOS TIA(R_f~kΩ)近乎无惩罚——但两者")
print("        靠调 R_E/R_f 都能压到 <20% 基底; 决定性差异仍是 ③ 节点可得 与 ② 负载/1/f\n")

print("════ 更优方案 C: 电流模差分读出（负权重本就强制, 一举三得）════")
print("  结构: 差分电流缓冲(半+权重, 半-权重), 输出 I+ - I-")
print("  ① 电流模本征(与 crossbar 电流和匹配, 无需 I→V) → 消解 MOS 的模态失配")
print("  ② 共模抑制 ~40dB → R0 共模漂移/温度/工艺 offset 被抵消(比单端强)")
print("  ③ 增益管可选 BJT(45nm, 1/f 低) 或 MOS(7/3nm, 纯 CMOS) → 节点无关")
print("  结论: 控制模态问题被架构消解——信号全程保电流模, 差分抵消共模, BJT/MOS 退化为选型")
print("\n════ 更优方案 D: 电荷采样(电流模 S/H, 零阻抗转换)════")
Csh = 10e-12
print(f"  结构: 虚地电流 I_sig 流进采样电容 C 时间 τ → V=I_sig·τ/C (天然跨阻, 无 R_f 热噪声)")
print(f"  噪声 = kT/C = {np.sqrt(kB*T/Csh)*1e3:.2f}µV(对 V); 全程电流模, 与差分结合 = 最优前端")

print("\n════ 总判定（含可行性）════")
print("  45nm 原型: BJT 电流模差分读出(1/f 最低, 本征匹配, 可得) → 方案可行")
print("  7/3nm   : MOS 电流模差分 TIA(纯 CMOS 可得, 差分抵消, R_f 调小噪声→无惩罚) → 可行")
print("  最优前端: 电流模 + 差分 + (可选电荷采样) → 控制模态失配被架构完全消解")
print("  附带红利: 注意力 softmax 的 exp 可用二极管(Schottky) I∝e^{V/VT} 原生实现")
