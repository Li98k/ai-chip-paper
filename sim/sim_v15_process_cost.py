# -*- coding: utf-8 -*-
"""R14: 成熟工艺节点 + 流片成本分析（Qwen3.8-27B, 270亿参数 = 270亿个存储单元）
用户问: 从现在成熟的芯片制作工艺和成本分析, 包括 ~24nm / 14nm。
方法: 在 sim_v12 面积模型(1 参数=1 单元, 面积 ∝ node², 锚定 45nm=4µm²)基础上
  外推 28nm(≈24nm 档)/14nm 成熟节点, 叠加 300mm 晶圆成本 + Poisson 良率 +
  858mm² reticle die 的 MCM 封装成本, 给出"一颗 27B 推理芯片"的硅+封装成本量级。
全部为【显式假设的估算】(非实测), 假设集中在下方 ASSUME 区, 可改。
"""
CM2 = 1e4            # 1 m² = 1e4 cm²
RETICLE_CM2 = 8.58   # 26×33 mm² = 858 mm²
DIE_MM2 = 858.0
R_WAFER = 150.0      # 300mm 晶圆半径 mm

# ── 假设区（可改）──
# 单元面积 µm²/参数: 锚定 45nm=4µm²(v6), 面积 ∝ node², 7/3nm 用 v6 锚点
CELL_UM2 = {"45nm":4.0, "28nm":4.0*(28/45)**2, "14nm":4.0*(14/45)**2,
            "7nm":0.1, "3nm":0.04}
WAFER_USD = {"45nm":1800, "28nm":2800, "14nm":4500, "7nm":10000, "3nm":18000}
D0 = {"45nm":0.07, "28nm":0.10, "14nm":0.13, "7nm":0.18, "3nm":0.23}  # 缺陷密度 /cm²
P = 27e9
A_DIE_CM2 = DIE_MM2/100.0   # 8.58 cm²

# reticle die 每晶圆个数（圆形晶圆, 858mm² 方 die）
import math
def dies_per_wafer(A_mm2, R=R_WAFER):
    return max(1.0, math.pi*R*R/A_mm2 - math.pi*R/math.sqrt(2*A_mm2))
NPW = dies_per_wafer(DIE_MM2)

print(f"每 reticle die = {DIE_MM2:.0f}mm² ({A_DIE_CM2:.2f}cm²); 300mm 晶圆 ≈ {NPW:.0f} 个 reticle die")
print(f"良率模型: Poisson Y=exp(-D0·A), A={A_DIE_CM2:.2f}cm²\n")
hdr = (f"{'节点':6s}{'单元µm²':>8s}{'总面积cm²':>10s}{'reticle':>9s}"
       f"{'晶圆$':>8s}{'D0':>6s}{'良率':>7s}{'单die$':>9s}{'硅成本$':>9s}{'MCM封$':>9s}{'总成本$':>9s}")
print(hdr); print("-"*len(hdr))
rows=[]
for node in ["45nm","28nm","14nm","7nm","3nm"]:
    cell = CELL_UM2[node]                 # µm²
    area_cm2 = P*cell*1e-8                # cm² = 27e9 × 4µm² × 1e-8 = 1080 (45nm 锚点, 同 v6/v12)
    ret = area_cm2/RETICLE_CM2
    wf  = WAFER_USD[node]
    d0  = D0[node]
    y   = math.exp(-d0*A_DIE_CM2)
    gdie= wf/(NPW*y)                       # 单个好 reticle die 成本
    sil = ret*gdie                         # 全部 reticle die 硅成本
    pkg = 200 + 55*ret                     # MCM 封装(基板/互连/探针/测试/返修) 粗估
    tot = sil+pkg
    rows.append((node,cell,area_cm2,ret,wf,d0,y,gdie,sil,pkg,tot))
    print(f"{node:6s}{cell:8.2f}{area_cm2:10.0f}{ret:9.1f}{wf:8d}{d0:6.2f}"
          f"{y:7.3f}{gdie:9.0f}{sil:9.0f}{pkg:9.0f}{tot:9.0f}")

print("\n════ 成本排序（一颗 27B 推理芯片, 硅+MCM 封装, 量产量级估算）════")
for r in sorted(rows, key=lambda x:x[-1]):
    print(f"  {r[0]:5s}: 总 ~${r[10]:6.0f}  (硅 ${r[8]:.0f} + MCM ${r[9]:.0f})  "
          f"[{r[3]:.1f} reticle die, 良率 {r[6]*100:.0f}%, 单die ${r[7]:.0f}]")

print("""
判读:
 · 45nm 最贵: 126 reticle die 的巨型 MCM, 封装+互连成本主导(即便晶圆最便宜)。
 · 28nm/14nm 也不便宜: 49/12 个 reticle die, MCM 封装吃掉晶圆单价优势。
 · 7nm/3nm 最省: 只需 ~3.1/1.3 个 reticle die, 虽单 die 贵但总成本最低。
 · 成本甜点 = 7–14nm 区间(成熟节点并非更便宜), 45nm 仅实验室原型。
 结构性优势: 本芯片【无 HBM/显存】(权重在硅片内), 不含 H100 的 8×HBM3
 (~$5–8k) 成本——这是"参数即电阻"相对 H100 的结构性成本红利。
 前提: 面积为"小区域阻性单元"(ReRAM/浮栅/小薄膜, ~0.04–4µm²/参数)口径;
 若用大尺寸蛇形 NiCr 薄膜(每 MΩ ~mm²), 面积与成本将成倍上升。
 良率: Poisson Y=exp(-D0·A), reticle 8.58cm² 大 die 良率本就低, 量产靠
 chiplet/binning/多 die 冗余改善——本估算偏保守(上限), 实际量产成本更低。
""")
