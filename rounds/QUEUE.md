# R16 线程任务清单（每轮领取第一个未勾选任务）

规则：
- 一轮只做一件事，做完把 [ ] 改成 [x]，并在文件末尾"领取记录"追加一行（UTC 时间 + 任务号 + 一句结果）。
- 产出物写入 rounds/ 或修改 paper.md/paper_en.md/README.md/sim/，最后 `git add -A && git commit -m "R16-Tn: ..."`。
- 铁律：不得改动任何仿真数值锚点，除非你用 .venv/bin/python 实际复跑脚本并以脚本输出为准。
- 数值口径权威源：sim_v10（SNR）、sim_v16（深度/余弦分布）、sim_v5b（容差 mean/p95）。

- [x] T1 新建 rounds/可行性与转换原理.md 并写第 1 章：电压→电流域转换原理
      （I_j=x_j/R_j 注入、虚地恒压≈V_BE 为何使求和精确、朴素电压模为何指数失真；配 sim_v1/v1b/v5 数据）
- [x] T2 第 2 章：电流域求和与容差统计红利（独立误差 Σ~√W vs 信号~W 的抵消推导 + sim_v5b MC 实测复核）
- [x] T3 第 3 章：BJT 跨导读出与线性化（g_m=IC0/VT、R_E 负反馈压非线性、电流镜差分读出）+ ADC 数字岛采样与 ENOB 口径
- [ ] T4 第 4 章：层间链路的域转换闭环（L2 电压输出→电阻网络→再电流化；逐层误差传播，引用 sim_v11 的 1e-16 恒等与 v16 分布）
- [ ] T5 第 5 章：可行性判定总装（器件小面积假设、工艺 3–5nm 分界、热、良率/成本、vs H100；给出"条件可行"四条件清单）
- [ ] T6 全文数值锚点复审：paper.md/paper_en.md/README.md 三套文档逐一对照最新 sim 输出，修一切不一致（跑 .venv/bin/python rounds/consistency_check.py --full 起步）
- [ ] T7 新增 sim/sim_v17_joint_noise.py：温度(65/85/105°C)×1-f 噪声×权重漂移(0/1/5%) 对最终余弦的联合影响（基于 v16 框架，多种子≥8 网络），结果写入第 5 章
- [ ] T8 审稿人红队：找 10 个最致命质疑（漂移、标定、编程吞吐、串扰 sneak path、良率、ADC 功耗、编译工具链、模型适配性、与 HBM/GPU 成本对比、安全），写入 rounds/redteam.md；对每条给出"已有证据/需补实验/承认为局限"三选一
- [ ] T9 按 redteam.md 中"需补实验"条目补 sim_v18+ 或文档回应；"承认为局限"条目写入 paper.md §6.3 局限性
- [ ] T10 终稿整合：可行性与转换原理.md 收尾摘要置顶；README 加链接；rounds/LOG.md 记 R16；git commit 收尾

若队列全部完成：执行滚动优化——复跑 consistency_check.py --full、挑 paper.md 任一章节做"去水分/补出处"精修一轮、commit。

## 领取记录

- 2026-10-22 06:05 UTC | T1 | 新建 rounds/可行性与转换原理.md 第 1 章（电压→电流域转换原理）：复跑 sim_v1/v1b/v4/v5/v5b，虚地精确性 0.00000000%、朴素指数失真 5.5×、倒灌 1.10mA/节点、β^L 爆炸全部实测入文；consistency_check CLEAN。
- 2026-10-22 06:55 UTC | T2 | 第 2 章「电流域求和与容差统计红利」：复跑 sim_v5b C5 复核权威口径（1%: 0.543/1.314，0.1%: 0.052/0.132）；新增 rounds/t2_tol_wscale.py W 标度实验（256~16384），归一 RMS/tol 平坦 0.54~0.60（理论 1/√3）、绝对误差 ∝√W、相干失配 0.87·tol·√W（W=4096@1%→55%）三类情形入文；consistency_check CLEAN。
- 2026-10-22 07:15 UTC | T3 | 第 3 章「BJT 跨导读出与线性化 + ADC/ENOB 口径」：复跑 sim_v4（S2 非线性列 2.714/0.146/0.247/0.010/0.037）、sim_v14（12.8µA/34.3nA/51.5dB、R_E/R_f 噪声惩罚、镜比±1-2%）、sim_v9/v10（ENOB 锚点 33.3/44.5/53.3dB）；新增 rounds/t3_readout_linear.py（环路增益 A=1+(1+1/β)gmRE 3~102、gm'平坦度±0.11%@A=102、非线性×A 标度、ENOB=(SNR−1.76)/6.02 复核、增益误差堆叠 ±2~3% 系统性无√W红利）；发现 kT/C 单位勘误（sim_v14 打印 0.02µV 应为 √(kT/C)=20.4µV，paper 三处沿袭，列入 T6 修）；consistency_check CLEAN。
