import json
import re

with open(".ai/qodo_raw_comments.json", "r", encoding="utf-8") as f:
    data = json.load(f)

issue_comments = data.get("issue_comments", [])
review_comments = data.get("review_comments", [])

md = []
md.append("# Qodo AI Code Review Findings — Pull Request #2\n")
md.append("**PR URL:** https://github.com/pranavsinghpatil/Harness-Agent/pull/2  ")
md.append("**Reviewer:** Qodo Code Review Bot (`qodo-ai`)  ")
md.append("**Target Branch:** `feature/simulation-sandbox` → `main`  \n")
md.append("---\n")

md.append("## 📊 Executive Summary of Review\n")
md.append("Qodo AI performed an automated deep code review of the **Virtual Hardware Simulation Sandbox** PR, identifying actionable improvement areas across:\n")
md.append("1. **Documentation & Public API Contracts (Rule Violations):** Docstring completeness on non-trivial methods (`run_episode`, `step`, `evaluate`, etc.).")
md.append("2. **Logic & Edge Cases:** Robust handling of zero/negative time intervals, state mutation side-effects, boundary wall tolerances, and queue lifecycle.")
md.append("3. **Code Cleanliness & Redundant Comments:** Removing comments that merely restate code.")
md.append("4. **Type Consistency & Return Signatures:** Explicit typing across sensor packets, telemetry frames, and replay comparison structures.\n")
md.append("---\n")

md.append("## 📋 Comprehensive Findings & Agent Remediation Prompts\n")

# Parse issue comments for detailed structured findings
count = 0
for c in issue_comments:
    body = c.get("body", "")
    blocks = re.findall(r"<details>\s*<summary>\s*(\d+\..*?)</summary>(.*?)</details>", body, re.DOTALL)
    for title, content in blocks:
        count += 1
        # Extract title text cleanly
        clean_title = re.sub(r"<.*?>", "", title).strip()
        
        desc_match = re.search(r"<pre>\s*(.*?)\s*</pre>", content, re.DOTALL)
        desc = desc_match.group(1).replace("\n", " ").strip() if desc_match else ""
        desc = re.sub(r"<.*?>", "", desc)

        code_match = re.search(r"<code>\[(.*?)\]\((.*?)\)</code>", content)
        code_file = code_match.group(1) if code_match else ""
        code_link = code_match.group(2) if code_match else ""

        rule_match = re.search(r"<code>Rule \d+: \[(.*?)\]\((.*?)\)</code>", content)
        rule_text = rule_match.group(1) if rule_match else ""
        rule_link = rule_match.group(2) if rule_match else ""

        prompt_match = re.search(r"## Issue description\s*(.*?)\s*## Issue Context\s*(.*?)\s*## Fix Focus Areas\s*(.*?)\s*```", content, re.DOTALL)
        prompt_desc = prompt_match.group(1).strip() if prompt_match else ""
        prompt_ctx = prompt_match.group(2).strip() if prompt_match else ""
        prompt_focus = prompt_match.group(3).strip() if prompt_match else ""

        md.append(f"### Finding {count}: {clean_title}\n")
        if code_file:
            md.append(f"- **Target Location:** [`{code_file}`]({code_link})")
        if rule_text:
            md.append(f"- **Rule:** [{rule_text}]({rule_link})")
        md.append(f"- **Description:** {desc}\n")
        
        if prompt_desc or prompt_ctx or prompt_focus:
            md.append("#### 🤖 Qodo Agent Remediation Context:")
            md.append("```markdown")
            md.append(f"Issue: {prompt_desc}")
            md.append(f"Context: {prompt_ctx}")
            md.append(f"Focus: {prompt_focus}")
            md.append("```\n")
        md.append("---\n")

# Parse inline review comments
md.append("## 💬 Inline Review Threads\n")
for idx, rc in enumerate(review_comments):
    path = rc.get("path", "")
    line = rc.get("line") or rc.get("original_line")
    body = rc.get("body", "")
    url = rc.get("html_url", "")
    
    md.append(f"### Inline Thread #{idx+1}: `{path}:{line}`\n")
    md.append(f"- **File:** [{path} (Line {line})]({url})")
    md.append(f"- **Reviewer Feedback:**\n\n{body}\n")
    md.append("---\n")

output_path = ".ai/qodo/pr2_review_findings.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

print(f"Generated {output_path} with {count} structured findings and {len(review_comments)} inline threads.")
