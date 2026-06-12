import sys
import json
import re

output_path = sys.argv[1]
countries_path = sys.argv[2]

with open(output_path, 'r', encoding='utf-8') as f:
    content = f.read()

with open(countries_path, 'r', encoding='utf-8') as f:
    countries = json.load(f)

MIN_NODES_FOR_GROUP = 5
standard_codes = {"HK", "TW", "JP", "SG", "US"}

# Separate into large (≥ threshold) and small (< threshold + UN)
large = [
    c for c in countries
    if c["code"] not in standard_codes
    and c["code"] != "UN"
    and c.get("count", 0) >= MIN_NODES_FOR_GROUP
]
small = [
    c for c in countries
    if c["code"] not in standard_codes
    and (c.get("count", 0) < MIN_NODES_FOR_GROUP or c["code"] == "UN")
]

if not large and not small:
    content = re.sub(r'^# __DYNAMIC_GROUPS__\s*\n', '', content, flags=re.MULTILINE)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("No additional country groups to add.")
    sys.exit(0)

# Build dedicated groups for large countries
dynamic_lines = []
for nc in large:
    gname = f"{nc['emoji']} {nc['name']}节点"
    dynamic_lines.append(
        f"  - name: {gname}\n"
        f"    type: url-test\n"
        f"    use:\n"
        f"      - ConfigForge\n"
        f"    filter: '(?i)^\\[{nc['code']}\\]'\n"
        f"    url: https://cp.cloudflare.com/generate_204\n"
        f"    interval: 300\n"
        f"    tolerance: 50"
    )

# Build 🌍 其他地区 group for small countries
if small:
    small_codes = [c["code"] for c in small]
    other_filter = "(?i)^\\[(" + "|".join(sorted(small_codes)) + ")\\]"
    dynamic_lines.append(
        f"  - name: 🌍 其他地区\n"
        f"    type: url-test\n"
        f"    use:\n"
        f"      - ConfigForge\n"
        f"    filter: '{other_filter}'\n"
        f"    url: https://cp.cloudflare.com/generate_204\n"
        f"    interval: 300\n"
        f"    tolerance: 50"
    )

dynamic_block = "\n".join(dynamic_lines)

# Replace marker with generated groups
content = re.sub(
    r'^# __DYNAMIC_GROUPS__\s*\n',
    dynamic_block + '\n\n',
    content,
    flags=re.MULTILINE
)

# Inject group names into 🚀 节点选择's proxies list (before 🔯 故障转移)
new_names = [f"{nc['emoji']} {nc['name']}节点" for nc in large]
if small:
    new_names.append("🌍 其他地区")

fault_tolerance_line = re.search(r'^(\s+)- 🔯 故障转移', content, re.MULTILINE)
if fault_tolerance_line:
    indent = fault_tolerance_line.group(1)
    insert_lines = ''.join(f"{indent}- {name}\n" for name in new_names)
    content = content[:fault_tolerance_line.start()] + insert_lines + content[fault_tolerance_line.start():]

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)

parts = []
if large:
    parts.append(f"{len(large)} dedicated: {[c['code'] for c in large]}")
if small:
    parts.append(f"other: {[c['code'] for c in small]}")
print(f"Injected {len(new_names)} groups ({'; '.join(parts)})")
