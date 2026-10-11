import re, json
data = open("elhalfawy-v20.html", "r", encoding="utf-8", errors="replace").read()
rows = json.load(open("_audit/images.json", encoding="utf-8"))

# 1) parse the asset table: q4=Object.assign({"./img/name.jpg":var,...}
m = re.search(r'q4=Object\.assign\(\{', data)
seg = data[m.end():m.end() + 6000]
end = seg.index("}")
table = seg[:end]
pairs = re.findall(r'"\./img/([^"]+)":([A-Za-z_$][A-Za-z0-9_$]*)', table)
name2var = {n: v for n, v in pairs}
print("table entries:", len(pairs))

# 2) var -> data URI offset (from audit), var name parsed from text before the URI
var2off = {}
off2var = {}
for r in rows[:51]:
    pre = r["pre"]
    mm = re.search(r'([A-Za-z_$][A-Za-z0-9_$]*)=$', pre[:-1] if pre.endswith('"') else pre)
    v = mm.group(1) if mm else None
    var2off[v] = r["off"]
    off2var[r["off"]] = v

missing = [n for n, v in name2var.items() if v not in var2off]
print("names without offset:", missing)
print("vars without name:", [v for v in var2off if v not in set(name2var.values())])

result = [dict(name=n, var=v, off=var2off[v], i=[r["i"] for r in rows if r["off"] == var2off[v]][0]) for n, v in name2var.items()]
json.dump(result, open("_audit/name_map.json", "w"), indent=1)
for r_ in sorted(result, key=lambda x: x["i"]):
    print(f"{r_['i']:>3} {r_['var']:<4} {r_['name']}")
