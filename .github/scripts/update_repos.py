#!/usr/bin/env python3
"""
Vampire Profile — Auto Repo Sync Script
GitHub থেকে repo তথ্য নিয়ে README এর PINNED_REPOS section আপডেট করে।
profile-config.yml এর নিয়ম অনুযায়ী repo ফিল্টার হয়।
"""

import os, requests, yaml, re
from datetime import datetime

# ── Config ────────────────────────────────────────────────
USERNAME  = os.environ.get("GITHUB_USERNAME", "muhammadshourov404")
TOKEN     = os.environ.get("GITHUB_TOKEN", "")
CONFIG    = "profile-config.yml"
README    = "README.md"
HEADERS   = {"Authorization": f"token {TOKEN}"} if TOKEN else {}
# ──────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch_repos():
    url   = f"https://api.github.com/users/{USERNAME}/repos"
    repos = []
    page  = 1
    while True:
        r = requests.get(url, headers=HEADERS, params={"per_page": 100, "page": page})
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos

def should_show(repo, cfg):
    name   = repo.get("name", "").lower()
    topics = repo.get("topics", [])

    # নিজের প্রোফাইল repo বাদ
    if name == USERNAME.lower():
        return False

    # পিন করা repo সবসময় দেখাবে
    if name in [p.lower() for p in cfg.get("pinned", [])]:
        return True

    # হাইড লিস্টে আছে?
    if name in [h.lower() for h in cfg.get("hidden", [])]:
        return False

    # হাইড prefix আছে?
    for prefix in cfg.get("hidden_prefix", []):
        if name.startswith(prefix.lower()):
            return False

    # হাইড topic আছে?
    for ht in cfg.get("hidden_topics", []):
        if ht.lower() in topics:
            return False

    # Fork লুকাবে?
    if repo.get("fork") and not cfg.get("show_forks", False):
        return False

    # Archived লুকাবে?
    if repo.get("archived") and not cfg.get("show_archived", False):
        return False

    # Required topics চেক
    required = cfg.get("required_topics", [])
    if required:
        if not any(rt.lower() in topics for rt in required):
            return False

    return True

def sort_repos(repos, cfg):
    sort_by = cfg.get("sort_by", "stars")
    if sort_by == "stars":
        return sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
    elif sort_by == "updated":
        return sorted(repos, key=lambda r: r.get("updated_at", ""), reverse=True)
    elif sort_by == "created":
        return sorted(repos, key=lambda r: r.get("created_at", ""), reverse=True)
    return repos

def build_markdown(repos, cfg):
    pinned_names = [p.lower() for p in cfg.get("pinned", [])]
    pinned = [r for r in repos if r["name"].lower() in pinned_names]
    others = [r for r in repos if r["name"].lower() not in pinned_names]

    max_r  = cfg.get("max_repos", 6)
    shown  = (pinned + others)[:max_r]

    lines = [
        f"> 🤖 *Auto-synced — {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC*\n",
        "<table><tr>"
    ]
    for i, repo in enumerate(shown):
        star  = repo.get("stargazers_count", 0)
        fork  = repo.get("forks_count", 0)
        lang  = repo.get("language") or "N/A"
        desc  = repo.get("description") or "No description."
        url   = repo.get("html_url", "#")
        name  = repo.get("name", "")
        is_pin = name.lower() in pinned_names

        pin_badge = "📌 " if is_pin else ""
        lines.append(f"""<td width="50%" valign="top">

**{pin_badge}[{name}]({url})**

{desc}

![Stars](https://img.shields.io/badge/⭐-{star}-00ff41?style=flat-square&labelColor=0d1117)
![Forks](https://img.shields.io/badge/🍴-{fork}-00bfff?style=flat-square&labelColor=0d1117)
![Lang](https://img.shields.io/badge/Lang-{lang}-ffffff?style=flat-square&labelColor=0d1117)

</td>""")
        if (i + 1) % 2 == 0 and i + 1 < len(shown):
            lines.append("</tr><tr>")

    lines.append("</tr></table>")
    return "\n".join(lines)

def update_readme(new_block):
    with open(README, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- PINNED_REPOS_START -->).*?(<!-- PINNED_REPOS_END -->)"
    replacement = f"<!-- PINNED_REPOS_START -->\n{new_block}\n<!-- PINNED_REPOS_END -->"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)
    print("✅ README.md updated successfully.")

if __name__ == "__main__":
    print("🧛 Vampire Bot — Syncing repos...")
    cfg   = load_config()
    repos = fetch_repos()
    print(f"📦 Total repos found: {len(repos)}")
    visible = [r for r in repos if should_show(r, cfg)]
    visible = sort_repos(visible, cfg)
    print(f"✅ Visible repos: {len(visible)}")
    block = build_markdown(visible, cfg)
    update_readme(block)
