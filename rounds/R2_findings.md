# R2 论证轮（2026-10-09 22:55–23:10）：文献定位与先例网络

## 1. 决定性发现：用户方案的"电路描述"在权威文献中原样存在
Bowen et al., "Analog, In-memory Compute Architectures for AI" (arXiv 2302.06417,
Neurophos/Duke, 我抓了全文 full_2302.06417.txt)，Fig.1(b) 图注原文：
  "Each transistor is connected to a reconfigurable resistor, the conductance
   of which determines the effective weight of each element in the matrix."
→ 这正是用户"三极管+可调电阻=权重"的原型描述。论文定位时必须引用并区分。

## 2. 该文献给出的定量锚点（可直接进论文）
- 模拟 CIM 的能效优势是**规模论证**（scaling argument）：
  e_op ∝ 1/N，N=算子规模/处理器规模（取小者）。
- **固定权重、永不重配置**时（= 用户"参数写入芯片"场景）：
  E_op = N·(e_dac,1 + e_adc) —— 只有输入 DAC 与输出 ADC 能耗，权重零能耗。
  这是用户方案相对 RRAM 可重配置方案（还要付 e_dac,2 配置能量）的**独特优势**。
- 但 Amdahl 式极限：即使访存能耗→0，计算能耗仍限制总能效；
  且当芯片装不下整个网络、需反复重配置时，O(N) 优势被破坏（→ 大模型需大芯片）。
- Table 4（45nm/0.9V/8bit 参考值）：
  SRAM 访问 4.3pJ，数字 MAC 0.23pJ，ADC 0.25pJ，DAC 0.01pJ，
  模拟负载能耗 0.04–0.8pJ（随 pitch/N 变化）。
- 精度：模拟优势集中在"大规模线性算子 + 低比特"（引 Hamerly 2019）。
- 符号问题的权威表述："memristor 器件只能存正数"（只能存正权重）
  → 负权重必须差分对/正负拆分（与我 R1 结论一致，文献背书）。

## 3. 标志性先例（技术谱系，论文 Related Work 用）
- ANNA (1989, IEDM)：16000 突触、电阻即权重 —— 最早的模拟 NN 芯片
  （arXiv 无此文献，来自领域先验，引用时标注 IEEE IEDM）
- IBM NorthPole (Shafiee et al. 2016 ISSCC)：256×256 ReRAM 模拟脉动加速器
- Mythic (Demler 2018, "Mythic multiplies in a flash", Microprocessor Report)：
  Flash crossbar 商用模拟推理芯片 —— Bowen 文引用，可作二手引用
- 2026 前沿（本次检索到，arXiv 一手）：
  * 模拟 LLM 适配 / 模拟训练规模化 系列（见 refs/arxiv_*.xml）
  * FORMS (2021)：偏置 ReRAM 细粒度混合信号 DNN 加速（符号问题的工程解法）
  * "Statistical Tc Distribution in Analog RRAM Array" (2021)：RRAM 温度
    漂移对精度影响 —— 对应我的"阻值漂移/校准"论点
  * 时间域模拟加权求和 PWM VLSI (2018/2019)：非 crossbar 的模拟加权求和路线

## 4. 失配/容差问题的文献解法（1606.07786 全文已抓）
"Precise NN computation with imprecise analog devices" (1606.07786):
- 把**实测器件失配作为约束并入 NN 训练**（mismatch-aware training），
  无需专门最小化失配 → 电路复杂度与功耗降到最小
- 可重构突触电路：3bit 精度，增益由数字信号 w±, wi 设定
- MNIST 196-200-200-10 网络验证：激活电路(soma)斜率失配固定后训练即可补偿
→ 对应我的 C5 结论（1% 容差→1.3% 误差），文献给出"训练侧吸收失配"的
  工程路径，比"买 0.1% 电阻"更便宜，应列为推荐方案之一。

## 5. 检索限制（诚实记录）
- Wikipedia / Google Scholar / IEEE Xplore 在本机网络不可达
  （仅 arXiv API + ar5iv 可用），ANNA/NorthPole/Mythic 的一手原文未抓到，
  论文引用时需用 DOI 核对（我给出的是领域共识条目）。
- ar5iv 有 ID 漂移风险（1606.07285 给错了内容，改按标题精确搜索才命中
  1606.07786）——后续引用一律以 abs 页核对。
