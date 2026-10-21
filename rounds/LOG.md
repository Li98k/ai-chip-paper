R0 start
task spec written
R0 findings written (1791555844)
R1 complete: sim v4+v5b + 4 figures (1791557475)
R2 landmark search running (1791557726)
R2 complete: lit deep-read + Bowen Table4 (1791558415)
R4/R5 complete: v6 designspace + v7 e2e + v8 errdecomp + v9/v10 SNR (1791558600)
R6 start: cross-check self-review (1791560800)
R6 checkpoint: paper.md v1 + refs/die-math corrected (1791561268)
R7 start: SNR 常数纠错 0.0289→0.0577(6dB) + ENOB 统一 6.02N+1.76 (median 49.9/37.9/25.8)
R7 checkpoint: v6/v9/plot_figs/paper 窗口口径统一 median 288kΩ@10MOPS, ≤2.9MOPS
R8: 三层布线原理图 fig3layer_wiring + sim_v11 数值验证 (z=W2·W1·x 误差 1e-16)
R9: 电路图实例 fig_circuit_flow (x_j→电阻→求和→BJT放大 传输流程) + 渲染器包围盒自检 0 重叠
R10: Qwen3.8-27B 核算 sim_v12 (面积 1m²=1e4cm² 修正; SNR 锚定验证窗口; 功率/吞吐/能效 vs H100)
R11: 发热 sim_v13 (风冷热阻 H100 校准, SNR∝1/√T 符号, TSV pitch 20µm; 3D 占位↓3.8×/体积↓2.2×) + 器件替代
R12: 控制模态 sim_v14 (BJT 电流 vs MOS 电压, 两模态均可行, 差分消解, BJT 调 R_E≥280Ω→-1dB / MOS TIA→0dB) + 写入 paper §4.4–4.7 + 摘要/§6.1
R13: 最优读出前端图 8 fig_readout_diff (差分电流模+电荷采样, CHECK 0 重叠) 写入 §4.7 + 附录; 全篇总结
R14: 工艺+成本 sim_v15 (28/14nm 外推 + Poisson 良率 + MCM 封装; 成熟节点不便宜, 甜点 7nm~$2.4k) + 修正能效单位(H100 实为 J/token, 之前误 mJ 错 1000×) + 吞吐(tok/s) + 改标题 + 新 §4.5 工艺成本
R15: 复跑审计+修复 (2026-10-21):
  - sim_v5.py 崩溃修复 (w 为 ndarray 非 Series, R0/0 inf 链; 改电导域直算 G=w/R0)
  - 图字体修复 (mpl 字体缓存未注册 Noto CJK; 清缓存+font list 加 JP/Droid 兜底, 16 图重出, 视觉复检 0 豆腐块)
  - sim_v5b C5 补 0.1% 容差扫描: 实测 mean/p95 = 0.54/1.31%@±1%, 0.05/0.13%@±0.1% (论文旧值 1.32% 实为 p95)
  - sim_v12 修复: TOPS 误乘致 N_nodes²虚高 7.7e6× (6.4e10→9.8e3 TOPS); ADC 136nJ→136pJ 单位错 (INT8 ADC<0.1% 才与"可忽略"自洽)
  - 新增 sim_v16_depth_multiseed.py: v7(0.889)/v8(0.791) 矛盾定论=单网络实现差异非模型差异;
    10 网络×20 MC 权威值: 0.829±0.024 @BW1.6M(≈3.2MOPS), 1MOPS 恢复 mean 0.928 (跨种子稳定)
  - 文档同步 12+ 处 (paper/paper_en/README): 2.56mA→1.10/−0.02mA, 1.32%→mean0.54/p95 1.31, 0.79→0.829±0.024,
    ISAAC(ISCA 2016)/NorthPole(IBM 2019+ 数字) 拆分勘误, 158TOPS/W 无出处删除, 附录补 v16
