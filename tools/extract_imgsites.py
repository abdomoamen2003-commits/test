import re
data = open("elhalfawy-v20.html", "r", encoding="utf-8", errors="replace").read()
out = []
for m in re.finditer(r'jsx\("img",\{', data):
    s = m.start()
    # take a window; find matching close of the props object by brace depth
    i = data.index("{", s)
    depth = 0
    end = i
    in_s = None
    while end < len(data):
        ch = data[end]
        if in_s:
            if ch == "\\":
                end += 2; continue
            if ch == in_s:
                in_s = None
        elif ch in "\"'`":
            in_s = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        end += 1
    out.append((s, data[s:end+1]))
    # skip past
out.sort()
print("total jsx img sites:", len(out))
with open("_audit/imgsites.txt", "w", encoding="utf-8") as f:
    for n, (s, txt) in enumerate(out):
        line = data[:s].count("\n") + 1
        f.write(f"\n===== SITE {n} (line {line}, offset {s}, len {len(txt)}) =====\n{txt}\n")
        # 300 chars before for component context
        f.write("--- before ---\n" + data[max(0, s-300):s].replace("\n", " ") + "\n")

# also: style background-image usages referencing asset resolver
print("--- backgroundImage / url( usages ---")
for m in re.finditer(r'backgroundImage[^,;}]{0,120}', data):
    print(repr(m.group(0)[:120]))
print("--- data:image in CSS style tag (line 278 area) ---")
for m in re.finditer(r'\.([A-Za-z0-9_\-]+)\{[^{}]{0,80}url\(data:image', data):
    print(m.group(1), m.start())
