# sales-engine: rules for agents

- Personal data (LinkedIn export, engine.db, queues, results, replies, scoreboard) lives only in git-ignored `data/`, `out/`, `inbox/`. Never commit it, never paste it into issues or PRs, never publish the scoreboard.
- Stdlib-only Python 3.10+. No new dependencies: it must run inside Cowork and on Windows without installs.
- Messaging rules live in `templates.json` and `COWORK.md`; volume and safety limits in `config.json`. Do not raise volume defaults or remove the stop-on-warning rule without the owner asking.
- Scoring logic is in `engine/classify.py` and documented in `PLAYBOOK.md §3`. Keep both in sync.
- Run `python -m unittest discover tests` before committing.
