#!/usr/bin/env python3
"""R2: 从已抓 arXiv XML 提取摘要，并补做批判性检索（模拟方案的极限/为何未胜出）"""
import re, pathlib, urllib.request, urllib.parse, time
OUT=pathlib.Path("/home/chiva/AI_video/AI_chip_paper/refs")

def parse(fname):
    t=(OUT/fname).read_text()
    entries=re.findall(r"<entry>(.*?)</entry>", t, re.S)
    out=[]
    for e in entries:
        idm=re.search(r"<id>(.*?)</id>", e)
        ti=re.search(r"<title>(.*?)</title>", e, re.S)
        su=re.search(r"<summary>(.*?)</summary>", e, re.S)
        pub=re.search(r"<published>(.*?)</published>", e)
        out.append({
            "id": idm.group(1).strip() if idm else "",
            "title": re.sub(r"\s+"," ",ti.group(1)).strip() if ti else "",
            "summary": re.sub(r"\s+"," ",su.group(1)).strip() if su else "",
            "pub": pub.group(1)[:10] if pub else ""})
    return out

print("# 已抓论文摘要（节选关键）\n")
KEYWORDS=["analog","in-memory","matrix","transistor","BJT","resistor","LLM","precision","SNR","Mythic","NorthPole"]
for f in sorted(OUT.glob("arxiv_*.xml")):
    for p in parse(f):
        blob=(p["title"]+" "+p["summary"]).lower()
        # 只要和"模拟/存内/电阻/三极管/精度"强相关的
        score=sum(1 for k in KEYWORDS if k in blob)
        if score>=3 and ("analog" in blob or "in-memory" in blob or "resist" in blob):
            print(f"[{p['pub']}] {p['title'][:90]}")
            print(f"   {p['summary'][:500]}")
            print(f"   {p['id']}\n")
