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
