import json
import re

with open(".ai/qodo_raw_comments.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Analyze Issue Comments
issue_comments = data.get("issue_comments", [])
review_comments = data.get("review_comments", [])

parsed_findings = []

# Parse main Qodo review comment
for c in issue_comments:
    body = c.get("body", "")
    # Look for details tags
    blocks = re.findall(r"<details>\s*<summary>\s*(\d+\..*?)</summary>(.*?)</details>", body, re.DOTALL)
    for title, content in blocks:
        # Extract description, code, evidence, agent prompt
        desc_match = re.search(r"<pre>\s*(.*?)\s*</pre>", content, re.DOTALL)
        desc = desc_match.group(1).replace("\n", " ").strip() if desc_match else ""
        
        prompt_match = re.search(r"## Issue description\s*(.*?)\s*## Issue Context\s*(.*?)\s*## Fix Focus Areas\s*(.*?)\s*```", content, re.DOTALL)
        prompt_desc = prompt_match.group(1).strip() if prompt_match else ""
        prompt_ctx = prompt_match.group(2).strip() if prompt_match else ""
        prompt_focus = prompt_match.group(3).strip() if prompt_match else ""

        parsed_findings.append({
            "title": title.strip(),
            "description": desc,
            "prompt_description": prompt_desc,
            "prompt_context": prompt_ctx,
            "prompt_focus": prompt_focus,
            "type": "issue_finding"
        })

# Parse inline review comments
for idx, rc in enumerate(review_comments):
    path = rc.get("path", "")
    line = rc.get("line") or rc.get("original_line")
    body = rc.get("body", "")
    parsed_findings.append({
        "title": f"Inline Comment on {path}:{line}",
        "path": path,
        "line": line,
        "body": body,
        "type": "inline_comment"
    })

print(f"Parsed {len(parsed_findings)} findings and comments.")
with open(".ai/parsed_qodo_findings.json", "w", encoding="utf-8") as f:
    json.dump(parsed_findings, f, indent=2)
