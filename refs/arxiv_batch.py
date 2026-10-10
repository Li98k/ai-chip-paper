#!/usr/bin/env python3
"""arXiv 批量检索：电阻/模拟/三极管 + 神经网络/AI 芯片 相关主题"""
import urllib.request, urllib.parse, re, time, pathlib

BASE = "https://export.arxiv.org/api/query"
OUT = pathlib.Path(__file__).parent

QUERIES = {
    "1_analog_mvm": 'all:"analog" AND all:"matrix-vector multiplication" AND cat:cs.LG',
    "2_resistive_neural": 'all:"resistive network" AND all:"neural network" AND all:"inference"',
    "3_transistor_nn": 'all:"transistor" AND all:"neural network" AND all:"analog circuit"',
    "4_rram_llm": 'all:"in-memory computing" AND all:"LLM" AND all:"inference"',
    "5_bjt_circuit_ml": 'all:"BJT" AND all:"deep learning"',
    "6_analog_precision_snr": 'all:"analog compute" AND all:"precision" AND all:"SNR"',
    "7_weights_as_resistor": 'all:"weight" AND all:"resistor" AND all:"analog" AND all:"inference chip"',
    "8_mysic_northpole": 'all:"Mythic" OR all:"NorthPole" OR all:"Syntiant" AND all:"analog" AND all:"AI"',
    "9_analog_training": 'all:"analog training" AND all:"in-memory"',
    "10_digital_analog_hybrid_llm": 'all:"hybrid digital-analog" AND all:"accelerator" AND all:"LLM"',
}

for name, q in QUERIES.items():
    url = BASE + "?" + urllib.parse.urlencode({
        "search_query": q, "start": 0, "max_results": 8,
        "sortBy": "relevance"})
    try:
        with urllib.request.urlopen(url, timeout=40) as r:
            data = r.read().decode()
    except Exception as e:
        print(f"{name}: FAIL {e}")
        time.sleep(2)
        continue
    (OUT / f"arxiv_{name}.xml").write_text(data)
    titles = re.findall(r"<title>(.*?)</title>", data, re.S)[1:]
    pubs = re.findall(r"<published>(.*?)</published>", data)
    print(f"== {name} ({len(titles)} hits)")
    for t, p in zip(titles, pubs):
        print(f"   [{p[:10]}] {t.strip()[:110]}")
    time.sleep(3)   # arXiv API 礼貌间隔
