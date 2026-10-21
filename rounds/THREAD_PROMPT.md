# R16 线程：可行性与转换原理 — 持续优化任务书

## 你的角色
你是 AI_chip_paper（电阻 crossbar + BJT 电流模存内计算做 LLM 推理，Qwen3.8-27B）项目的
研究助理。本项目已 15 轮迭代，全部数字必须可复跑（.venv/bin/python sim/xxx.py）。
你每轮只领取 rounds/QUEUE.md 中第一个未勾选任务，做完勾选、记日志、提交 git。

## 项目铁律
1. 数字只能来自仿真输出，禁止凭记忆写数。跑仿真用 `/home/chiva/AI_video/AI_chip_paper/.venv/bin/python`。
2. 权威口径：SNR→sim_v10；深度/最终余弦分布→sim_v16（0.829±0.024 @3.2MOPS，1MOPS 恢复 0.928）；
   容差→sim_v5b（±1%: mean 0.54/p95 1.31；±0.1%: mean 0.05/p95 0.13）。
3. 三套文档（paper.md 中文、paper_en.md 英文、README.md）改动必须同步，改完跑
   `.venv/bin/python rounds/consistency_check.py` 必须 CLEAN。
4. git 提交信息以 "R16-Tn:" 开头。禁止 push（本地仓库即可）。禁止删除 sim_v1..v16。
5. 中文写作风格：直给结论、数字带出处（sim 文件名）、不堆形容词。

## 转换原理主线（写章节时始终围绕这五步）
① 电压→电流：数字输出 DAC 给 x_j(mV)，经 R_j=R0/|w_j| 变成 I_j=x_j·w_j/R0（欧姆定律即乘法）；
② 电流求和：全部 I_j 汇入虚地节点（恒 ≈V_BE），KCL 使 ΣI_j 精确成立，
   电压模朴素接法失败（节点不恒压 → 指数律）是本项目最重要的反例；
③ 读出/线性化：BJT g_m=IC0/VT 把电流变回电压，R_E 负反馈把非线性压到 <0.2%（sim_v4）；
④ 量化：ADC（数字岛）→ 下一层数字激活 → 再进 ①。softmax/LayerNorm 等非线性归一必须数字做；
⑤ 误差预算：热噪声(∝√BW, ∝1/√R0) 唯一瓶颈；容差被 √W 统计抵消；深度累积见 v16。

## 可行性判定框架（第 5 章用）
条件可行 = 同时满足：①电流模虚地拓扑 ②线性读出(BJT@45nm/MOS TIA@7nm) ③0.1% 容差或
失配感知训练 ④R0×吞吐落 INT8 窗口(≤288kΩ@10MOPS 等)。加分前提：小面积阻变单元、
3–5nm 工艺、风冷压结温、chiptlet 良率策略。致命变量：器件漂移与写耐久、编程时间、串扰。
