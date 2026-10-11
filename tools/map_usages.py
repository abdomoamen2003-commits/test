import re, json, collections

data = open("elhalfawy-v20.html", "r", encoding="utf-8", errors="replace").read()
rows = json.load(open("_audit/images.json", encoding="utf-8"))

# map: var name -> image index  (pattern: VAR="data:image/...")
varmap = {}
for r in rows[:51]:
    m = re.search(r'([A-Za-z_$][A-Za-z0-9_$]{0,3})="data:image/', r["pre"] + 'X')
    # pre ends with ...VAR="  -> grab trailing identifier before ="
    m2 = re.search(r'([A-Za-z_$][A-Za-z0-9_$]*)=$', r["pre"])
    varmap[r["i"]] = m2.group(1) if m2 else "?"
print("var map:", {k: v for k, v in varmap.items()})

# find usages: count occurrences of each var after its definition
for i, r in enumerate(rows[:51]):
    v = varmap[i]
    if v == "?" or not v:
        continue
    # usages = occurrences of , VAR or {VAR or (VAR etc, excluding the definition
    occ = [m.start() for m in re.finditer(r'(?<![A-Za-z0-9_$])' + re.escape(v) + r'(?![A-Za-z0-9_$])', data)]
    ctxs = []
    for o in occ[:6]:
        ctxs.append(data[max(0, o - 70):o + 40].replace("\n", " ")[-110:])
    print(f"--- #{i:>2} {v:<3} size={r['w']}x{r['h']} occ={len(occ)}")
    for c in ctxs[1:4]:
        print("      ", c)
