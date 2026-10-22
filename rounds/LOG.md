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
R16: 可行性与转换原理专章 + 红队 + 补实验 (2026-10-22, 5h 自动线程 + 收官):
  - 新增 rounds/可行性与转换原理.md 五章: ①电压→电流域转换(欧姆定律即乘法, 虚地KCL精确,
    30级往返零拓扑深度罚 2.66e-15) ②电流求与容差统计红利(W标度实验: 归一误差/tol平坦≈0.58, 绝对∝√W,
    相干失配 0.87·tol·√W 边界) ③BJT跨导读出与线性化(环路增益A=3~102, gm平坦度±0.11%@A=102,
    增益误差±2~3%系统性无√W红利, ENOB复核) ④层间域转换闭环(深度累积100%热噪声, 存量传播1.13~1.29×/层,
    复合增速=σ恒定÷信号0.65×/层收缩; 逐层满摆幅复位 0.829→0.9899 正交恢复杠杆) ⑤可行性判定总装
    (4硬条件C1~C4 + 4加分P1~P4 + 3致命变量D1~D3, 判定式, vs H100对照表, 9条工程核对单) + 收尾摘要置顶
  - 新增 rounds/redteam.md 审稿人红队 10 致命质疑(Q1漂移/Q2标定/Q3编程/Q4列线sneak/Q5缺陷/Q6 ADC/
    Q7 KV回流/Q8合成余弦≠困惑度/Q9 NRE/Q10防逆向), 每条三选一处置; 量级推演: 编程18.3h@1e4脉冲,
    列线悲观角IR降26%, KV 2.52TB/s回流, 注意力MAC仅7.7%
  - 补实验 sim_v18~v22 (E系列, 锚点自检 0.8291 全对齐):
    v18 漂移时间轴(独立失配5年κ=0.3末期0.8288, 0.1%角5年稳0.8291) / v19 列线RC(最坏410Ω仅0.046%p95,
    C1稳健) / v20 缺陷注入(stuck-open 1e-4无损0.8294, 1%→0.8096, 5%→0.7431) / v21 标定闭环(q≥4bit
    即贴热噪声天花板0.8298≈理想0.8295, 标定收益本征小) / v22 KV回流+编程墙钟+NRE摊销(INT8@4k
    2.52TB/s可行, INT4档需分片; 编程16s行并行/18.3h串行, 写能0.0022kWh; NRE$1亿盈亏平衡4.2万颗)
  - 文档: paper/paper_en §6.3 10行→15行(并入E1~E5定量缓解+L1~L4局限声明), 附录补v18~v22,
    仿真计数19→24(README/paper头部/paper_en头部); 修复 v22 B节单位笔误; README 加专章/红队链接
  - 线程机制: rounds/watcher.sh 看门狗(串行派工/断点自恢复/失败熔断) + rounds/consistency_check.py
    门禁(--full 扫禁用旧数字+复跑5权威脚本) + QUEUE.md 任务队列; 实际运行 05:53→11:40 UTC = 5h47m
R17: 滚动优化轮 (队列10/10 完成后收尾, 2026-10-22):
  - 门禁: consistency_check.py --full 复跑 → VERDICT CLEAN (禁数字扫描 + v11恒等1.16e-16
    + 全量复跑 v5b/v10/v16/v12, 锚点 0.8291 对齐)
  - §5 文献定位精修(去水分/补出处, 中英同步 paper.md/paper_en.md §5.1): 核对了 Bowen
    2302.06417 已抓全文的参考列表, 原文实际仅引用谱系表中的 ISAAC(2016)/Mythic(2018)/
    Xia&Yang(2019) 三行; ANNA(1989)/1990s模拟VLSI/Hopfield/NorthPole/1606.07786 均不在其
    参考列表(grep 各 0 命中)。修正 §5.1 表前导语, 不再笼统称"该文献引用的标志性工作",
    改为明确区分"项目补充的谱系定位" vs "Bowen 原文引用", 消除出处归属歧义(审稿人可核查)。
  - 注: ANNA 1989 具体规格(16000突触/双极)项目一手未抓到(见 R2/R6), 已在参考文献标注
    "cited from public historical record"; 本表仅修正归属, 不新增未核实数字。
  - 未动仿真口径与任何数值锚点; consistency_check --full 复跑 CLEAN。
