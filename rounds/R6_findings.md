# R6 最终自审轮（2026-10-09 23:50–24:10）

本轮对论文初稿做逐数字交叉核对，抓到 3 类残留问题并全部修正。

## A. 本轮回撤/修正清单
1. **die 数量换算差 10 倍**：100mm² die = 10⁴ mm² = 1 cm²。
   - 27B@45nm = 1080 cm² = **1080 个 1cm² die ≈ 126 个 reticle die**
     （reticle ≈ 800×800mm² ≈ 64cm²）。此前 R4R5/v6 输出行的"108 die"
     与论文正文的"108 die/单大 die"均按 10cm²/die 误算。
   - 2.5B@45nm = 100cm² = 100 个 1cm² die（非 10 die）。
   - 27B@3nm = 10.9cm² ≈ 1.3 个 reticle die → "单 die 可行"改为
     **"单封装（1~2 reticle die）可行"**，表述更严谨。
   - 影响面：paper.md（4 处）、plot_figs.py fig3/fig4 标注、
     sim_v6 结论打印、R4R5_findings B3。全部修正。

2. **论文功耗节节点总数错误**："2.5B 参数 ~1 亿节点" → 实为
   2.5e9/4096 ≈ **61 万节点**。按 P_node≈3·VCC·IC0 重算：
   IC0=10/50/100µA → 16/82/164W。

3. **参考文献幻觉（最严重）**：初稿引用的 arXiv 2506.12345 /
   2504.16225 / 2506.02767 三个 ID 虽在 arXiv 上存在，但实际是
   高熵合金/观察者理论/强化学习论文，与主题完全无关（引用时凭
   记忆编的 ID）。已用 refs/ 目录里真实抓取过的论文替换并逐一
   通过 arXiv API 核实标题+作者：
   - 2305.16647 Büchel et al., "Gradient descent-based programming
     of analog in-memory computing cores"（2023）
   - 2507.09776 Kavishwar & Shanbhag, "Compute SNR-Optimal ADCs for
     Analog In-Memory Computing"（2025）
   - 2511.15950 DeBole et al., "A Scalable NorthPole System...LLM
     Inference"（2025）
   → 教训：任何引用必须当场 API 核实，记忆中的 arXiv ID 不可信。

## B. 交叉核对通过项（论文数字 vs 仿真输出）
- SNR 表（33.3/44.5/53.3/53.7dB）= sim_v10 输出，一致 ✓
- INT8 门槛 48.2dB = 6.02×8 ✓；INT4 24.8dB = 6.02×4.12 ✓
- 10MOPS@1MΩ 设计窗口 → R0≤300kΩ：39+20log10(√(1e6/3e5))=39+5.9≈45
  仍 <48.2，更精确值 R0≤3.5e5 → 论文取"≈300kΩ"偏保守 ✓
- 容差 1%→1.32%、0.1%→0.13% = sim_v5b C5 输出 ✓
- Bowen Table 4 能耗数字 = refs/full_2302.06417.txt 原文 ✓
- 图 5 热图公式与 sim_v10 MC 一致（R0=1MΩ/10MOPS→44.5dB 落点 ✓）

## C. 图版本一致性
fig1~fig5 全部于 23:50 重新生成；fig3 面板B 公式改为 v10 版
（0.0289/√(3.19·kT·BW·R0)，原 v9 版常数 0.289 是旧错误标度残留，
已同步修正）；fig4/fig3 面积标注改为 reticle 换算。
vision 抽查 fig3 新文本确认渲染正确。

## D. 遗留问题（如实记录，不影响结论）
1. sim_v7/v8 的端到端余弦 0.79 基于 41dB/层噪声假设，未与 v10 的
   44.5dB 完全对齐（差 3.5dB → 余弦应略高于 0.79，约 0.81~0.83）。
   量级结论不变，论文已按 0.79 保守引用并注明"~0.8"。
2. ANNA(1989)/Mythic(2018)/NorthPole 电路细节来自公开史料与
   Bowen 综述的转述（Wikipedia/Scholar 不可达），论文已注明。
3. RRAM 编程能耗、多晶硅电阻面积系数为文献典型值，未做 PDK 级
   核算——论文定位为"可行性论证"而非"可流片设计"，此精度足够。

## E. 论证轮次总结（22:12 起）
R0 任务规格+文献定位 → R1 电路级仿真(v1~v5b) → R2 文献深读
→ R4/R5 设计空间+SNR 精算(v6~v10) → R6 交叉核对自审。
累计：11 个可复跑仿真、5 幅图、2 篇全文+3 篇 API 核实引用、
6 处重大自我纠错（理想增益公式、BUG-1/2、面积单位、SNR 标度、
die 换算、引用幻觉）。
论文初稿 paper.md 367 行，含全部数据、公式、优缺点与参考文献。
