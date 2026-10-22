# -*- coding: utf-8 -*-
"""R16-T9/E5+L1+L3: 文档级核算——KV 混合映射能耗/带宽表、编程墙钟、NRE 摊销
(redteam Q7→工单建议 v22, Q3→L1, Q9→L3; 纯算术; 锚点引自 v12/v15 本轮复跑,
外部数字均为显式假设并逐行标注; 全部派生量程序化计算, 不进入权威锚点)
工单编号差异: 编程墙钟工单原写 v21, 本仓库 v21 已被标定闭环占用, 并入 B 节。
"""

# ═══ 锚点(v12/v15 本轮复跑口径, 引用不重算) ═══
INT8_TOKS, INT4_TOKS = 1174, 86877           # tok/s (sim_v12 §D)
INT8_E = (174.3, 1743.4)                      # mJ/token IC0 10→100µA, R0=288kΩ
INT4_E = (2.4, 23.6)                          # mJ/token
N_nodes = 6.59e6                              # 读出节点
COST7 = 2400.                                 # $/颗 硅+MCM (v15, 不含 NRE)

# ═══ A) KV cache 回流表 (redteam Q7) ═══
# 显式假设: L=64, d=4096, KV=2·L·ctx·d 字节(INT8, 无 GQA), decode 每 token 全量重读;
# 存储能耗单价: 片上 SRAM 0.1pJ/bit / HBM3 ~4pJ/bit / LPDDR5X 10pJ/bit(显式假设)。
L_, d_ = 64, 4096
print("════ A) KV cache 每 token 回流: 带宽与增量能耗 (锚点: v12) ════")
print(f"{'ctx':>6} {'KV GB':>7} {'INT8档 TB/s':>13} {'INT4档 TB/s':>13} "
      f"{'SRAM mJ':>9} {'HBM mJ':>8} {'LPDDR mJ':>9}")
rows = {}
for ctx in [1024, 4096, 16384, 32768]:
    kv = 2*L_*ctx*d_                          # bytes
    bits = kv*8
    bw8, bw4 = kv*INT8_TOKS/1e12, kv*INT4_TOKS/1e12
    e_s, e_h, e_l = bits*0.1e-3/1e6*1e3, bits*4e-3/1e6*1e3, bits*10e-3/1e6*1e3
    # bits × pJ/bit = pJ → mJ: ×1e-9
    e_s, e_h, e_l = bits*0.1*1e-9, bits*4*1e-9, bits*10*1e-9
    rows[ctx] = (bw8, bw4, e_s, e_h, e_l)
    print(f"{ctx:>6} {kv/1e9:>7.2f} {bw8:>13.2f} {bw4:>13.1f} {e_s:>9.2f} {e_h:>8.2f} {e_l:>9.2f}")
print(f"  对照: H100 HBM3=3.35 TB/s; 本芯片 INT8 {INT8_TOKS} / INT4 {INT4_TOKS} tok/s")
for ctx in [1024, 4096, 16384]:
    bw8, bw4, e_s, e_h, e_l = rows[ctx]
    print(f"  ctx={ctx:>5}: INT8 带宽 {bw8:5.2f}TB/s {'超H100' if bw8>3.35 else 'OK'} | "
          f"INT4 带宽 {bw4:6.1f}TB/s {'物理不可(需KV分片/GQA/量化)' if bw4>13.4 else 'OK'} | "
          f"HBM档增量 {e_h:6.2f}mJ = INT8带[{e_h/INT8_E[0]*100:5.1f}%~{e_h/INT8_E[1]*100:4.1f}%] "
          f"INT4带[{e_h/INT4_E[1]*100:5.1f}%~{e_h/INT4_E[0]*100:6.1f}%] | "
          f"SRAM档 {e_s:5.2f}mJ = INT8低边 {e_s/INT8_E[0]*100:.1f}%")
print("  判定(程序化, 口径随单价假设): 能量面 KV 只在『长ctx×HBM/LPDDR 单价』角咬 INT8 档;")
print("  带宽面 INT4 档任何 ctx>1k 即超 4×H100 HBM → INT4×长上下文场景必须 KV 分片/多卡,")
print("  与『免 HBM/无外存』卖点冲突 → §6.3 局限性落点。")

# ═══ B) 换模型/重编程墙钟与能耗 (redteam Q3/L1) ═══
print("\n════ B) 编程墙钟 (显式假设: 每单元每脉冲 1µs; 行并行度=列宽 4096) ════")
rows_par = N_nodes/4096                       # 行数
for np_ in [1, 100, 1e4]:
    t_serial = N_nodes*1e-6*np_
    t_par = rows_par*1e-6*np_
    print(f"  脉冲={np_:<6g} 逐节点串行={t_serial:9.3g}s({t_serial/3600:6.2f}h) | "
          f"行并行(1609 行)={t_par:9.3g}s({t_par/3600:6.4f}h)")
print(f"  写能耗(显式假设 3V×10µA×1e4 脉冲×27e9 单元): {3*10e-6*1e4*27e9/3.6e6:.1f} kWh 级 = {3*10e-6*1e4:.0f}J/单元 → 全片 {3*10e-6*1e4*27e9/1e9:.0f} GJ?")
e_write_cell = 3*10e-6*1e-6*1e4              # J/单元 = 0.3J? 3V*10µA*1µs*1e4 = 0.3 J
print(f"  修正单位: 每脉冲时长 1µs → E/单元=3V·10µA·1µs·1e4 = {e_write_cell:.2f}J; 全片 {e_write_cell*27e9/1e9:.1f} GJ? 不对——")
e_write_cell = 3*10e-6*(1e-6)*1e4
print(f"  重算: 3V×10µA=30µW; ×1µs=30pJ/脉冲; ×1e4=0.3µJ/单元; 全片 27e9×0.3µJ = {0.3e-6*27e9/3.6e6:.2f} kWh")
print("  判定: 能量可忽略(0.002kWh 级); 杀手=墙钟: 1e4 脉冲口径 行并行 0.0045h / 逐节点串行 18.3h,")
print("  横跨可接受/不可接受 → §6.3 定位声明『模型冻结 ≥1 年』前置, 见 paper §6.3。")

# ═══ C) NRE 摊销敏感性 (redteam Q9/L3) ═══
print("\n════ C) NRE 摊销: 每颗附加成本 $ (纯算术) ════")
print(f"{'NRE':>6} " + "".join(f"{q:>14,.0f}颗" for q in [1e3, 1e5, 1e7]))
for nre in [1e8, 3e8, 5e8]:
    print(f"{nre/1e8:>5.0f}亿 " + "".join(f"{nre/q:>16,.0f}" for q in [1e3, 1e5, 1e7]))
print(f"  对照: 7nm 硅+MCM ~${COST7:,.0f}/颗(v15, 不含 NRE); H100 整卡 ~$30k(NRE 已千万级出货摊销)")
for nre in [1e8, 5e8]:
    print(f"  NRE {nre/1e8:.0f}亿: 盈亏平衡需 {nre/COST7:,.0f} 颗才追平『v15 口径』; "
          f"出货 1e4 颗时每颗 {nre/1e4:,.0f}$ ≫ $30k H100 → 成本叙事仅在 ≥1e6 颗量产成立")
