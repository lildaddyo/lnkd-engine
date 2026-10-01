# Set up LinkedIn Engine on the dedicated machine

**Setup:** you (Ilian), on a dedicated Claude.ai account and a dedicated machine. That machine becomes the **only** runner of the daily LinkedIn task. Nothing secret is in this file.

> ⚠️ **One runner only.** Never schedule the daily Cowork task on more than one machine for the same LinkedIn profile. Sequence state lives in the local `data/engine.db`, which git doesn't sync, so two runners would double-send. If any messages were already sent from another machine, copy that machine's `data/engine.db` here before step 3.

## 1. Before you start (one-time, about 10 min)

- [ ] **GitHub:** the new Claude account can access `lildaddyo/lnkd-engine` (claude.ai → Settings → Connectors → GitHub).
- [ ] **Python 3.10+** installed, with "Add to PATH" ticked.
- [ ] **Chrome** logged into your LinkedIn on this machine.
- [ ] **CRM connector:** claude.ai → Settings → Connectors → Add custom connector
  - Name: `VRX CRM Linkedin`
  - URL: `https://hiejpnpgroxgwaexdosm.supabase.co/functions/v1/crm-mcp?token=<LI token>`
  - Leave the OAuth fields empty.
  - Good moment to **rotate** the token: Lovable → VR Express CRM Suite → Cloud → Secrets → `MCP_SERVER_TOKEN_LI`, then Publish, then update every connector URL that uses it.
- [ ] Optional: the **VR Express** CRM connector too, needed only to rebuild `crm_warm.csv`.
- [ ] Put your LinkedIn export zip somewhere on this machine. You can copy it or re-download it: LinkedIn → Settings → Data privacy → Get a copy of your data.

## 2. Seed prompt (paste into Claude Code on this machine)

```
Set up my LinkedIn Engine on this machine. Don't send anything to LinkedIn.

1. Clone https://github.com/lildaddyo/lnkd-engine to C:\CLAUDE\lnkd-engine (git pull if it already exists).
2. Copy my LinkedIn export zip (ask me where it is if you can't find it in Downloads) to data\LinkedInExport.zip.
   Nothing in data\, out\ or inbox\ is ever committed.
3. If data\crm_warm.csv is missing and the "VRX CRM" (VR Express) connector is available, export contacts tagged
   tier:past-buyer and tier:dormant-client into it with columns name,company,role,tier,vertical,linkedin_url.
   Otherwise skip this step and tell me.
4. Run: py -m unittest discover tests  →  py -m engine import  →  py -m engine report --html  →  py -m engine export-crm
   Report: contacts imported, the track × grade table, how many CRM warm contacts matched, and the export-crm count
   (expect ~776). Open out\scoreboard.html for me.
5. Check the "VRX CRM Linkedin" connector: list_contacts limit 1 must show _workspace.label "LI" and total ~776.
   Don't push anything; the CRM is already seeded.
6. Run: py -m engine plan --force --dry-run (a preview that saves nothing). Show me 10 messages from
   out\dryrun_queue_<today>.csv, two each from REACTIVATE, WARM, ICP, PARTNER and STUDENT. Then stop.
```

## 3. Go live

1. Read the 10 sample messages. Fix any wording in `templates.json` (messages) or `config.json` (offers and client examples), then commit and push.
2. Cowork → new **scheduled task**: weekdays around 09:30, folder `C:\CLAUDE\lnkd-engine` attached, **VRX CRM Linkedin** connector on (not the VR Express one), and Chrome logged into LinkedIn.
3. Prompt: the **"Daily task prompt"** block from [COWORK.md](COWORK.md).
4. Watch the first run. Send-days 1–5 are capped at about 40 messages; after that it ramps up to 120–150 by send-day 21.
5. Each evening, check **Replies** in the CRM (LinkedIn Engine workspace) and approve the drafted responses.

## 4. What does NOT come through git

| Thing | Where | On this machine |
|---|---|---|
| Who was messaged (sequence state) | `data/engine.db` | Created by `engine import`. Copy it from the old machine only if that machine already sent messages. |
| LinkedIn export | `data/LinkedInExport.zip` | Copy it or re-download it |
| CRM warm list | `data/crm_warm.csv` | Rebuilt in seed step 3, or copy it |
| CRM token | Lovable secret + connector URL | Password manager only |
| Cowork scheduled task | Cowork, per account | Created in step 3 |

## Reference

[README.md](README.md) · [PLAYBOOK.md](PLAYBOOK.md) · [COWORK.md](COWORK.md) · [docs/CRM_WORKSPACE.md](docs/CRM_WORKSPACE.md). CRM workspace: **LinkedIn Engine** (`22630c16-3de9-4e00-ad16-2975bac06d1f`).
