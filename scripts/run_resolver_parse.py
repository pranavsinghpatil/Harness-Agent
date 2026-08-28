import subprocess
import json
import re

p1 = subprocess.run(["gh", "api", "repos/pranavsinghpatil/Harness-Agent/issues/2/comments", "--paginate"], capture_output=True, text=True, encoding="utf-8")
comments = json.loads(p1.stdout) if p1.stdout else []

p2 = subprocess.run(["gh", "api", "repos/pranavsinghpatil/Harness-Agent/pulls/2/comments", "--paginate"], capture_output=True, text=True, encoding="utf-8")
inline_comments = json.loads(p2.stdout) if p2.stdout else []

# Parse main Qodo review comment
review_body = ""
for c in comments:
    user = c.get("user", {}).get("login", "")
    if "qodo" in user or "pr-agent" in user:
        review_body = c.get("body", "")
        break

# Extract sections
# Qodo sections have shields.io badges: Action_required, Review_recommended, Optional
sections = re.split(r'<img src="https://img\.shields\.io/badge/([^"]+)"', review_body)

items_by_bucket = {}
if len(sections) > 1:
    for i in range(1, len(sections), 2):
        bucket_raw = sections[i].split("-")[0].replace("_", " ")
        content = sections[i+1]
        blocks = re.findall(r'<details>\s*<summary>\s*(\d+\..*?)</summary>(.*?)</details>', content, re.DOTALL)
        items_by_bucket[bucket_raw] = []
        for title, body in blocks:
            clean_title = re.sub(r'<.*?>', '', title).strip()
            loc_match = re.search(r'<code>\[(.*?)\]', body)
            loc = loc_match.group(1) if loc_match else "unknown"
            items_by_bucket[bucket_raw].append((clean_title, loc))
else:
    blocks = re.findall(r'<details>\s*<summary>\s*(\d+\..*?)</summary>(.*?)</details>', review_body, re.DOTALL)
    items_by_bucket["Findings"] = []
    for title, body in blocks:
        clean_title = re.sub(r'<.*?>', '', title).strip()
        loc_match = re.search(r'<code>\[(.*?)\]', body)
        loc = loc_match.group(1) if loc_match else "unknown"
        items_by_bucket["Findings"].append((clean_title, loc))

with open("docs/qodo/pr2_parsed_issues.json", "w", encoding="utf-8") as f:
    json.dump(items_by_bucket, f, indent=2)

print("Parsed buckets and items:")
for b, items in items_by_bucket.items():
    print(f"=== {b} ({len(items)} items) ===")
    for title, loc in items[:5]:
        print(f"  • {title} -> {loc}")
