# -*- coding: utf-8 -*-
"""T3 支撑实验：BJT 跨导读出的线性化参数与 ENOB 口径复核
A. 发射极退化 BJT 小信号参数：gm=IC0/VT、环路增益 1+gm'·RE、有效跨导
B. 大信号线性度：与 sim_v4 S2 同模型（Node 类同款）复现非线性列，
   叠加环路增益列，验证"非线性 ≈ 反比于环路增益"的标度
C. ENOB 口径：R7 闭合式 + v10 MC 锚点复核；INT8 门槛 = 6.02N+1.76 推导
D. 读出增益精度堆叠：电流镜镜比 ±1-2%、1/β 负载 ~1%（sim_v14 口径）
常数与 sim_v4 完全一致（IS=1e-14, BETA=100, T=300.15）。
"""
import numpy as np
q = 1.602e-19; kB = 1.381e-23; T = 300.15; VT = kB * T / q
BETA = 100.0; VCC = 1.8
IS = 1e-14
def ic_of_vbe(v): return IS * np.exp(np.clip(v, -0.2, 0.92) / VT)

class Node:
    """与 sim_v4.Node 同模型（发射极退化 + 二分自洽解）"""
    def __init__(self, w, R0, R_E):
        self.w = w; self.R0 = R0; self.R_E = R_E
        self.Rw = R0 / w
        self.G = np.sum(1.0 / self.Rw)
    def _vbe(self, vb):
        vbe = 0.6
        for _ in range(60):
            ic = ic_of_vbe(vbe)
            f = vbe + ic * (1 + 1.0 / BETA) * self.R_E - vb
            df = 1.0 + ic / VT * (1 + 1.0 / BETA) * self.R_E
            s = f / df; vbe -= s
            if abs(s) < 1e-14: break
        return vbe
    def solve(self, x, ibias):
        S = np.sum(x / self.Rw); G = self.G
        def F(vb): return S + ibias - vb * G - ic_of_vbe(self._vbe(vb)) / BETA
        lo, hi = 1e-3, VCC - 0.05
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if F(lo) * F(mid) <= 0: hi = mid
            else: lo = mid
        vb = 0.5 * (lo + hi); vbe = self._vbe(vb); ic = ic_of_vbe(vbe)
        return ic, vb, vbe
    def design(self, xbar, IC0):
        VBE0 = VT * np.log(IC0 / IS)
        VB0 = VBE0 + IC0 * (1 + 1.0 / BETA) * self.R_E
        ibias = (VB0 - xbar) * self.G + IC0 / BETA
        return VBE0, VB0, ibias

print("=" * 84)
print("A. 发射极退化 BJT 小信号参数（VT = %.2f mV, gm=IC0/VT, A=1+(1+1/β)·gm·RE）" % (VT * 1e3))
print(f"  {'RE':>6} {'IC0':>7} {'gm(mS)':>7} {'环路增益A':>9} {'gmp(mS)':>8} {'|dgmp/gmp|@+-10%IC':>18}")
for RE, IC0 in [(260, 200e-6), (1000, 200e-6), (2600, 200e-6),
                (260, 1e-3), (1000, 1e-3), (2600, 1e-3)]:
    gm = IC0 / VT
    A = 1 + (1 + 1 / BETA) * gm * RE
    gmp = gm / A
    # 跨导对工作点的敏感度：IC ±10% 时 gm' 的相对变化（增益平坦度）
    d = max(abs((gm * f / (1 + (1 + 1 / BETA) * gm * f * RE)) / gmp - 1) for f in (0.9, 1.1))
    print(f"  {RE:5.0f}Ω {IC0*1e6:6.0f}µA {gm*1e3:7.2f} {A:9.2f} {gmp*1e3:8.3f} {d*100:16.2f}%")

print("=" * 84)
print("B. 大信号线性度复现（sim_v4 S2 同模型：W=4096,R0=1MΩ,x~U(0,100mV),0→满幅15点）")
rng = np.random.default_rng(7)  # 与 sim_v4 同种子同权重
w = np.clip(rng.normal(1.0, 0.6, 4096), 0.1, 4.0)
xref = rng.uniform(0, 100e-3, 4096)
print(f"  {'RE':>6} {'IC0':>7} {'非线性%':>8} {'环路增益A(工作点)':>15} {'非线性×A':>9}")
for RE, IC0 in [(260, 200e-6), (260, 1e-3), (1000, 200e-6),
                (1000, 1e-3), (2600, 200e-6), (2600, 1e-3)]:
    node = Node(w, 1e6, RE)
    VBE0, VB0, ibias = node.design(50e-3, IC0)
    pts = [node.solve(a * xref, ibias) for a in np.linspace(0, 1, 15)]
    vbs = np.array([p[1] for p in pts]); ics = np.array([p[0] for p in pts])
    if ics.max() - ics.min() < 1e-15:   # 与 sim_v4 同守卫：摆幅塌缩记 0（头空间不足所致）
        nl = 0.0
    else:
        k1, k0 = np.polyfit(vbs, ics, 1)
        nl = np.max(np.abs(k0 + k1 * vbs - ics)) / (ics.max() - ics.min()) * 100
    A = 1 + (1 + 1 / BETA) * (IC0 / VT) * RE
    print(f"  {RE:5.0f}Ω {IC0*1e6:6.0f}µA {nl:8.3f} {A:15.2f} {nl*A:9.1f}")

print("=" * 84)
print("C. ENOB 口径复核（R7 闭合式, R0=1MΩ; SNR_work = SNR_RMS − 2.5dB; ENOB=(SNR−1.76)/6.02）")
def snr_rms_dB(BW, R0): return 20 * np.log10(0.0577 / np.sqrt(3.1916 * kB * T * BW * R0))
def enob(db): return (db - 1.76) / 6.02
print("  锚点 vs v10 MC（100MOPS 33.3dB/5.2b | 10MOPS 44.5/7.1 | 1MOPS 53.3/8.6）：")
for ops in [100e6, 10e6, 1e6]:
    db = snr_rms_dB(ops / 2, 1e6) - 2.5
    print(f"    {ops/1e6:5.0f}MOPS: 闭合式 {db:5.1f}dB → ENOB {enob(db):4.1f} bit"
          f"   所需ADC N≥{int(np.ceil(enob(db)))}")
print(f"  INT8 门槛（满幅 SNR 下界）= 6.02×8+1.76 = {6.02*8+1.76:.1f} dB → 权威取 49.9 dB")
print(f"  INT6 = {6.02*6+1.76:.1f} dB（文档口径 37.9）；INT4 = {6.02*4+1.76:.1f} dB（口径 25.8）")

print("=" * 84)
print("D. 电流镜差分读出增益精度堆叠（sim_v14 口径：镜比 ±1-2%、1/β 负载 ~1%）")
for mirror, beta_err in [(1.0, 1.0), (2.0, 1.0)]:
    worst = mirror + beta_err
    rss = np.hypot(mirror, beta_err)
    print(f"  镜比±{mirror:.0f}% + 1/β±{beta_err:.0f}% → 最坏 ±{worst:.0f}%, RSS ±{rss:.1f}%"
          f"  vs v16/v7 建模的每层读出失配 ±1%")
print("  注: 该增益误差是逐层【系统性】误差(同号), 不享第2章 √W 统计红利;")
print("      差分拓扑共模抑制 ~40dB 只救共模漂移, 镜比失配需版图共质心+校准。")
