"""CLI: python -m engine <command>

  import   --export <zip|folder> [--connections Connections.csv] [--crm data/crm_warm.csv]
  plan     [--date YYYY-MM-DD] [--force] [--cap N] [--dry-run]     -> out/queue_<date>.json|csv + inbox/results_<date>.csv
  sync                                                  <- inbox/results_*.csv, inbox/replies_*.csv
  report   [--html] [--json]                            -> funnel + out/scoreboard.html
  mark     <profile_url> [--stage S] [--track T] [--lang bg|en]
  export-crm                                            -> out/crm_push.csv
  daily    [--date]                                     sync + plan + report --html (what Cowork runs)
"""
import argparse
import os
import sys
from datetime import date

from . import core, report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import")
    p.add_argument("--export", default=None)
    p.add_argument("--connections", default=None)
    p.add_argument("--crm", default=None)
    for name in ("plan", "daily"):
        p = sub.add_parser(name)
        p.add_argument("--date", default=None)
        p.add_argument("--force", action="store_true")
        p.add_argument("--cap", type=int, default=None)
        p.add_argument("--dry-run", action="store_true", help="preview only; writes out/dryrun_queue_*, saves nothing")
    sub.add_parser("sync")
    p = sub.add_parser("report")
    p.add_argument("--html", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("mark")
    p.add_argument("url")
    p.add_argument("--stage")
    p.add_argument("--track")
    p.add_argument("--lang")
    sub.add_parser("export-crm")
    a = ap.parse_args(argv)

    cfg = core.load_cfg()
    db = core.open_db()

    if a.cmd == "import":
        exp = a.export or _default(("data/LinkedInExport.zip", "data/export"))
        conn = a.connections or _default(("data/Connections.csv",))
        crm = a.crm or _default(("data/crm_warm.csv",))
        if not exp and not conn:
            sys.exit("No export found. Pass --export <zip|folder> or put it at data/LinkedInExport.zip")
        n, new = core.do_import(db, cfg, exp, conn, crm)
        print(f"Imported {n} people ({new} new). Sources: export={exp} connections={conn} crm={crm}")
        print(report.text(db))
    elif a.cmd in ("plan", "daily"):
        d = date.fromisoformat(a.date) if a.date else date.today()
        if a.cmd == "daily":
            print(_sync_text(core.sync(db, cfg)))
        items, msg = core.plan(db, cfg, d, force=a.force, cap_override=a.cap, dry_run=a.dry_run and a.cmd == "plan")
        print(msg)
        if items is not None:
            by = {}
            for it in items:
                by[(it["track"], it["touch"])] = by.get((it["track"], it["touch"]), 0) + 1
            print("  " + ", ".join(f"{t}#{n}={c}" for (t, n), c in sorted(by.items())))
            if a.dry_run:
                print(f"  preview: out/dryrun_queue_{d}.csv (nothing saved)")
            else:
                print(f"  queue: out/queue_{d}.json   results to fill: inbox/results_{d}.csv")
        if a.cmd == "daily":
            print("scoreboard:", report.html_scoreboard(db, cfg))
    elif a.cmd == "sync":
        print(_sync_text(core.sync(db, cfg)))
    elif a.cmd == "report":
        print(report.dump_json(db) if a.json else report.text(db))
        if a.html:
            print("scoreboard:", report.html_scoreboard(db, cfg))
    elif a.cmd == "mark":
        ok = core.mark(db, cfg, a.url, a.stage, a.track, a.lang)
        print("updated" if ok else "not found")
    elif a.cmd == "export-crm":
        p, n = report.export_crm(db)
        print(f"{n} contacts -> {p}")


def _default(cands):
    for c in cands:
        p = core.path(c)
        if os.path.exists(p):
            return p
    return None


def _sync_text(r):
    return (f"sync: sent={r['sent']} not_connected={r['not_connected']} skipped={r['skipped']} "
            f"replies={r['replies']} referrals={r['referrals']} files={r['files']}")


if __name__ == "__main__":
    main()
