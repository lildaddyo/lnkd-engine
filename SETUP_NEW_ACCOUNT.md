# Set up LinkedIn Engine on another Claude.ai account

For a second Claude.ai account (yours or a teammate's) that has access to this GitHub repo.
Nothing secret is stored in this file. The CRM token is handed over separately (see step 3).

## 0. Decide which case you're in. This changes steps 2 and 5.

| Case | Whose LinkedIn sends the messages | Engine data |
|---|---|---|
| **A: same person, new Claude account** (e.g. Ilian on a second account or machine) | Ilian's | Copy the existing `data/` folder over. Don't start fresh. |
| **B: another person runs their own network** | Theirs | Their own LinkedIn export, their own `data/`, and their own sender details in `config.json` and `templates.json` |

> ⚠️ **Only one runner per LinkedIn account.** Never run the daily Cowork task for the same LinkedIn profile from two accounts or machines. The engine's sequence state lives in the local `data/engine.db`, which git doesn't sync, so two runners would double-send.

## 1. Accounts and access checklist

| Item | Who grants it | How |
|---|---|---|
| GitHub repo `lildaddyo/lnkd-engine` | Repo owner | GitHub → Settings → Collaborators (already done if you can open this file) |
| Claude.ai account with **Claude Code** and **Cowork** | — | Paid plan with Claude Code and Cowork enabled |
| Claude Code ↔ GitHub | The new account | claude.ai → Settings → Connectors → GitHub, or `gh auth login` on the desktop |
| **VRX CRM app login**, LinkedIn Engine workspace | CRM owner (Ilian) | CRM → switch to *LinkedIn Engine* → Setup → **Users** → invite the new person's email. They'll see only that workspace's data. |
| **CRM connector token** | CRM owner | Use the existing `MCP_SERVER_TOKEN_LI`, or issue a separate one (see step 3) |
| Python 3.10+ on the desktop | — | python.org, with "Add to PATH" ticked |
| Chrome logged into the LinkedIn account that sends | — | Cowork drives this browser |

## 2. Get the engine running (desktop)

```bash
git clone https://github.com/lildaddyo/lnkd-engine
cd lnkd-engine
python -m unittest discover tests          # Windows: py -m unittest discover tests
```

**Case A (same person):** copy the whole `data/` folder from the current machine: `engine.db`, `LinkedInExport.zip` and `crm_warm.csv`. Run `py -m engine report --html` and check the numbers match the old machine. Don't re-import from scratch, because that loses who's already been messaged. After the copy, stop the old machine's Cowork task.

**Case B (new person):**
1. On LinkedIn, go to Settings → Data privacy → **Get a copy of your data** → *Download larger data archive* (it includes Connections.csv and messages). Save it as `data/LinkedInExport.zip`.
2. Edit `config.json` → `sender` (first name, BG name, company, LinkedIn URL, family surnames to exclude).
3. Edit `templates.json`. The messages are written in the first person as Ilian / VR Express, with claims like "8+ AI products live" and client names. Rewrite anything that isn't true for the new sender.
4. Run `py -m engine import`, then `py -m engine report --html`, then open `out/scoreboard.html`.

Optional, both cases (the CRM warm list): in a Claude chat that has the VR Express CRM connector, ask:
*"Export contacts tagged tier:past-buyer and tier:dormant-client to data/crm_warm.csv with columns name, company, role, tier, vertical, linkedin_url."* Then re-run `py -m engine import`.

## 3. Connect the CRM (claude.ai connector)

1. claude.ai → Settings → Connectors → **Add custom connector**
   - Name: `VRX CRM Linkedin`
   - URL: `https://hiejpnpgroxgwaexdosm.supabase.co/functions/v1/crm-mcp?token=<LI TOKEN>`
   - Leave the OAuth fields empty.
2. Test it in a chat: *"Use VRX CRM Linkedin → list_contacts limit 1."* The result must show `_workspace.label = "LI"`.
   - An **OAuth / "couldn't register" error** means the token is wrong. The server returned 401.

**Token handover:** the CRM owner sends the token through a password manager or 1Password share, **never in chat, email or the repo**.

**Recommended:** give each person their own token so it can be revoked individually. The server already supports per-person tokens for the VR Express workspace (`MCP_SERVER_TOKEN_VRE_GEORGI`), and adding `MCP_SERVER_TOKEN_LI_<NAME>` the same way is a one-line Lovable change. Ask Claude Code to do it with the lock protocol.

## 4. Dry run, with nothing sent

```bash
py -m engine plan --force
```
Open `out/queue_<date>.csv` and read 10–15 messages across tracks. Fix the wording in `templates.json` and `config.json` before any real send.

## 5. Schedule the daily Cowork task

- Cowork → new **scheduled task**, weekdays around 09:30 local time.
- Attach the `lnkd-engine` folder. Enable the **VRX CRM Linkedin** connector (never the VR Express one for this task). Chrome must be logged into the right LinkedIn account.
- Prompt: paste the **"Daily task prompt"** block from [COWORK.md](COWORK.md).
- Supervise the first run and watch the first ~5 messages go out.
- **Case B only:** in `data/engine.db` the ramp starts from day 1 automatically (about 40/day). Case A continues where the old machine left off.

## 6. What does NOT transfer through git

| Thing | Where it lives | How to move it |
|---|---|---|
| Sequence state, who was messaged | `data/engine.db` | Copy the file (case A only) |
| LinkedIn export | `data/LinkedInExport.zip` | Copy it (A) or download a new one (B) |
| CRM warm list | `data/crm_warm.csv` | Copy or regenerate (step 2) |
| Queues and results | `out/`, `inbox/` | Not needed; they're regenerated daily |
| CRM token | Lovable secret + connector URL | Password manager |
| Cowork scheduled task | Cowork (per account) | Recreate it (step 5) |

## 7. Reference

- How it works and why: [README.md](README.md), [PLAYBOOK.md](PLAYBOOK.md)
- Daily operation: [COWORK.md](COWORK.md)
- CRM workspace (views, data mapping, MCP tool): [docs/CRM_WORKSPACE.md](docs/CRM_WORKSPACE.md)
- CRM app: Lovable project "VR Express CRM Suite". Workspace **LinkedIn Engine** (`22630c16-3de9-4e00-ad16-2975bac06d1f`).
