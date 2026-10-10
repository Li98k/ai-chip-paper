#!/usr/bin/env python3
"""R2: 标志性先例 + 批判性极限 的针对性 arXiv 检索"""
import urllib.request, urllib.parse, re, time, pathlib
OUT=pathlib.Path("/home/chiva/AI_video/AI_chip_paper/refs")
BASE="https://export.arxiv.org/api/query"

# 用 title 精确/半精确搜索标志性工作
TARGETS={
 "anna_1989":      'ti:"artificial neural network" AND ti:"analog" AND abs:"16000"',
 "mythic":         'ti:"Mythic" AND abs:"analog" AND abs:"matrix"',
 "northpole":      'abs:"NorthPole" AND abs:"memory" AND abs:"LLM"',
 "true_north":     'ti:"TrueNorth"',
 "analog_neural_history": 'ti:"analog neural network" AND abs:"history"',
 "precision_limit":'abs:"analog in-memory" AND abs:"precision" AND abs:"limit"',
 "adc_overhead":   'abs:"in-memory computing" AND abs:"ADC" AND abs:"power"',
 "weight_program": 'abs:"crossbar" AND abs:"programming" AND abs:"memristor" AND abs:"neural"',
 "stochastic_bjt": 'abs:"stochastic" AND abs:"transistor" AND abs:"inference"',
 "log_domain":     'abs:"log-domain" AND abs:"multiply" AND abs:"analog"',
 "current_mode_ma":'abs:"current-mode" AND abs:"multiply-accumulate" AND abs:"analog" AND abs:"CMOS"',
 "virtual_ground": 'abs:"virtual ground" AND abs:"crossbar" AND abs:"analog"',
}
for name,q in TARGETS.items():
    url=BASE+"?"+urllib.parse.urlencode({"search_query":q,"start":0,"max_results":6,"sortBy":"relevance"})
    try:
        with urllib.request.urlopen(url,timeout=40) as r: data=r.read().decode()
    except Exception as e:
        print(f"{name}: FAIL {e}"); time.sleep(2); continue
    (OUT/f"arxiv_{name}.xml").write_text(data)
    entries=re.findall(r"<entry>(.*?)</entry>", data, re.S)
    print(f"== {name} ({len(entries)})")
    for e in entries:
        ti=re.search(r"<title>(.*?)</title>",e,re.S)
        pub=re.search(r"<published>(.*?)</published>",e)
        su=re.search(r"<summary>(.*?)</summary>",e,re.S)
        iid=re.search(r"<id>(.*?)</id>",e)
        t=re.sub(r"\s+"," ",ti.group(1)).strip() if ti else ""
        s=re.sub(r"\s+"," ",su.group(1)).strip()[:280] if su else ""
        print(f"   [{(pub.group(1)[:10] if pub else '?')}] {t[:95]}")
        print(f"      {s}")
        print(f"      {iid.group(1).strip() if iid else ''}")
    time.sleep(3)
