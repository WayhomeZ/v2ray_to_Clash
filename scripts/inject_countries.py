import sys
import json
import re

output_path = sys.argv[1]
countries_path = sys.argv[2]

with open(output_path, 'r', encoding='utf-8') as f:
    content = f.read()

with open(countries_path, 'r', encoding='utf-8') as f:
    countries = json.load(f)

standard_codes = {"HK", "TW", "JP", "SG", "US"}
new_countries = [c for c in countries if c["code"] not in standard_codes and c["code"] != "UN"]

# Remove the marker line if no new countries
if not new_countries:
    content = re.sub(r'^# __DYNAMIC_GROUPS__\s*\n', '', content, flags=re.MULTILINE)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("No additional country groups to add.")
    sys.exit(0)

# Build dynamic group YAML blocks
dynamic_lines = []
for nc in new_countries:
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

dynamic_block = "\n".join(dynamic_lines)

# Replace marker line with dynamic group YAML blocks
content = re.sub(
    r'^# __DYNAMIC_GROUPS__\s*\n',
    dynamic_block + '\n\n',
    content,
    flags=re.MULTILINE
)

# Inject new group names into 🚀 节点选择's proxies list
new_names = [f"{nc['emoji']} {nc['name']}节点" for nc in new_countries]
# Insert before 🔯 故障转移
fault_tolerance_line = re.search(r'^(\s+)- 🔯 故障转移', content, re.MULTILINE)
if fault_tolerance_line:
    indent = fault_tolerance_line.group(1)
    insert_lines = ''.join(f"{indent}- {name}\n" for name in new_names)
    content = content[:fault_tolerance_line.start()] + insert_lines + content[fault_tolerance_line.start():]

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Injected {len(new_countries)} dynamic country group(s): {[c['code'] for c in new_countries]}")
