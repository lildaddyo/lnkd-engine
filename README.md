# LinkedIn Network Sales Engine

A self-contained outreach engine for your LinkedIn network. It works like this:

**LinkedIn data export → per-person signals → prospect scoreboard → track → daily queue of 120–150 personalized DMs → Cowork sends → results and replies flow back → funnel and A/B learning.**

- Pure Python 3.10+ standard library, with no installs or API keys. It runs on your desktop, in Cowork, or in Claude Code.
- **Personal data never touches git.** `data/`, `out/` and `inbox/` are git-ignored. Only code, config and templates sync through GitHub.
- The evidence behind every rule is in [PLAYBOOK.md](PLAYBOOK.md), and Cowork's daily instructions are in [COWORK.md](COWORK.md).

## Quick start (desktop, after the GitHub sync)

```bash
git clone <repo> && cd sales-engine          # or: git pull
# put your LinkedIn export zip at data/LinkedInExport.zip
# optional: data/crm_warm.csv (VR Express past buyers / dormant clients)
python -m engine import                       # Windows: py -m engine import
python -m engine report --html                # opens out/scoreboard.html locally
python -m engine plan                         # today's queue -> out/queue_<date>.json
```

Then set up the Cowork scheduled task described in [COWORK.md](COWORK.md). Its daily command is `python -m engine daily`, which runs sync, plan and scoreboard in one go.

## Commands

| Command | What it does |
|---|---|
| `import [--export zip\|folder] [--connections csv] [--crm csv]` | Parses messages, invitations, endorsements, follows, Connections.csv and the CRM warm list, then scores everyone. Safe to re-run monthly because it never resets the funnel. |
| `plan [--date D] [--cap N] [--force]` | Builds the day's queue: due follow-ups first, then new first touches by `track_mix`, with A/B variants chosen by Thompson sampling. Writes `out/queue_D.json` and `.csv`, and `inbox/results_D.csv` for Cowork to fill. |
| `sync` | Reads `inbox/results_*.csv` (sent or skipped, plus profile data Cowork saw) and `inbox/replies_*.csv` (sentiment, next step, referrals), and moves contacts through the funnel. |
| `daily` | `sync` + `plan` + scoreboard. This is what Cowork runs. |
| `report [--html] [--json]` | Track × grade table, outreach funnel, and A/B results. `--html` writes `out/scoreboard.html`. |
| `mark <url> --stage MEETING \| --track ICP \| --lang en` | Manual override for one person. |
| `export-crm` | `out/crm_push.csv`: conversations, meetings and A-grade prospects for VRX CRM import. |

## Files

```
config.json      volume ramp, sequence timing, track mix, proof points, offers  ← tune here
templates.json   BG/EN messages per track × touch × variant                     ← write copy here
engine/          ingest.py (export parsing) · classify.py (scoreboard) · core.py (plan/sync) · report.py
tests/           synthetic end-to-end tests: python -m unittest discover tests
data/ out/ inbox/   private, git-ignored
```

## Moving it to its own repo

Right now this lives in `sales-engine/` inside another repo. To split it into its own private repo with history:

```bash
git subtree split --prefix sales-engine -b sales-engine-only
git push git@github.com:<you>/linkedin-sales-engine.git sales-engine-only:main
```
