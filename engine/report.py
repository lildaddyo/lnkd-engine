"""Funnel metrics + a self-contained HTML scoreboard (local file: it contains personal data)."""
import collections
import html
import json
import os
from datetime import date, timedelta

from .core import path, variant_stats
from .util import full_url

STAGES = ["NEW", "IN_SEQUENCE", "REPLIED", "CONVERSATION", "MEETING", "PROPOSAL", "WON",
          "LOST", "NURTURE", "NOT_CONNECTED", "DNC"]
TRACK_ORDER = ["REACTIVATE", "WARM", "ICP", "BUILDER", "PARTNER", "AUTO", "NETWORK", "STUDENT", "DNC"]


def metrics(db):
    m = {}
    m["by_stage"] = {r[0]: r[1] for r in db.execute("SELECT stage, COUNT(*) FROM contacts GROUP BY stage")}
    m["by_track"] = {r[0]: r[1] for r in db.execute("SELECT track, COUNT(*) FROM contacts GROUP BY track")}
    m["by_grade"] = {r[0]: r[1] for r in db.execute("SELECT grade, COUNT(*) FROM contacts WHERE track!='DNC' GROUP BY grade")}
    m["track_grade"] = collections.defaultdict(dict)
    for tr, g, n in db.execute("SELECT track, grade, COUNT(*) FROM contacts GROUP BY track, grade"):
        m["track_grade"][tr][g] = n
    m["fit_known"] = db.execute("SELECT COUNT(*) FROM contacts WHERE fit_known=1").fetchone()[0]
    m["total"] = db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    # outreach funnel per track (sequences started = touch-1 sent)
    started = {r[0]: r[1] for r in db.execute(
        "SELECT track, COUNT(DISTINCT key) FROM touches WHERE status='sent' AND touch=1 GROUP BY track")}
    replied = collections.Counter()
    positive = collections.Counter()
    for tr, sent in db.execute("SELECT t.track, r.sentiment FROM replies r JOIN touches t ON t.id=r.touch_id"):
        replied[tr] += 1
        if sent in ("positive", "referral"):
            positive[tr] += 1
    m["funnel"] = {tr: {"started": started.get(tr, 0), "replied": replied[tr], "positive": positive[tr]}
                   for tr in TRACK_ORDER if tr != "DNC"}
    m["variants"] = {f"{k[0]}/{k[1]}/{k[2]}": v for k, v in sorted(variant_stats(db).items())}
    since = (date.today() - timedelta(14)).isoformat()
    m["daily"] = [(r[0], r[1], r[2]) for r in db.execute(
        "SELECT plan_date, SUM(status='sent'), SUM(status LIKE 'skipped%') FROM touches "
        "WHERE plan_date>=? GROUP BY plan_date ORDER BY plan_date", (since,))]
    m["pipeline"] = {s: m["by_stage"].get(s, 0) for s in ("CONVERSATION", "MEETING", "PROPOSAL", "WON")}
    return m


def text(db):
    m = metrics(db)
    out = [f"Contacts: {m['total']}  (profile known: {m['fit_known']})", "",
           "Track        A    B    C    D   total"]
    for tr in TRACK_ORDER:
        g = m["track_grade"].get(tr, {})
        out.append(f"{tr:<11}" + "".join(f"{g.get(x, 0):>5}" for x in "ABCD") + f"{sum(g.values()):>8}")
    out += ["", "Stages: " + ", ".join(f"{s}={m['by_stage'][s]}" for s in STAGES if m["by_stage"].get(s))]
    f = [(tr, v) for tr, v in m["funnel"].items() if v["started"]]
    if f:
        out += ["", "Outreach     started  replied  reply%  positive"]
        for tr, v in f:
            out.append(f"{tr:<11}{v['started']:>9}{v['replied']:>9}{100 * v['replied'] / v['started']:>7.1f}%{v['positive']:>9}")
    if m["variants"]:
        out += ["", "A/B (touch 1)   sent  success  rate"]
        for k, (n, r) in m["variants"].items():
            out.append(f"{k:<16}{n:>5}{r:>9}{(100 * r / n if n else 0):>6.1f}%")
    return "\n".join(out)


def html_scoreboard(db, cfg, top=300):
    m = metrics(db)
    rows = db.execute("SELECT * FROM contacts WHERE track!='DNC' AND stage NOT IN ('LOST','NOT_CONNECTED') "
                      "ORDER BY score DESC LIMIT ?", (top,)).fetchall()
    e = html.escape

    def bar(v, mx, cls):
        return f'<span class="bar {cls}" style="width:{int(60 * (v or 0) / mx)}px" title="{v}"></span>'

    trs = []
    for r in rows:
        prof = r["headline"] or r["position"] or ""
        if r["company"] and r["company"] not in prof:
            prof = f"{prof} · {r['company']}" if prof else r["company"]
        trs.append(
            f"<tr data-track='{e(r['track'] or '')}'><td class=g{e(r['grade'] or 'D')}>{e(r['grade'] or '')}</td>"
            f"<td class=num>{r['score']}</td>"
            f"<td><a href='{e(full_url(r['key']))}' target=_blank rel=noopener>{e(r['name'] or r['key'])}</a>"
            f"<div class=sub>{e(prof or '— profile unknown —')}</div></td>"
            f"<td><span class='chip t-{e(r['track'] or '')}'>{e(r['track'] or '')}</span><div class=sub>{e(r['stage'] or '')}</div></td>"
            f"<td class=bars>{bar(r['s_rel'], 35, 'rel')}{bar(r['s_intent'], 25, 'int')}{bar(r['s_fit'], 30, 'fit')}{bar(r['s_timing'], 10, 'tim')}</td>"
            f"<td class=sub>{e(r['reasons'] or '')}</td><td class=sub>{e(r['next_action'] or '')}</td></tr>")
    kpis = [("Contacts", m["total"]), ("Profile known", m["fit_known"]),
            ("A-grade", m["by_grade"].get("A", 0)), ("In sequence", m["by_stage"].get("IN_SEQUENCE", 0)),
            ("Conversations", m["pipeline"]["CONVERSATION"]), ("Meetings", m["pipeline"]["MEETING"]),
            ("Proposals", m["pipeline"]["PROPOSAL"]), ("Won", m["pipeline"]["WON"])]
    kpi_html = "".join(f"<div class=kpi><b>{v}</b><span>{k}</span></div>" for k, v in kpis)
    tg = "".join(
        f"<tr><td><span class='chip t-{tr}'>{tr}</span></td>" + "".join(
            f"<td class=num>{m['track_grade'].get(tr, {}).get(g, 0)}</td>" for g in "ABCD")
        + f"<td class=num>{m['funnel'].get(tr, {}).get('started', 0)}</td>"
        + f"<td class=num>{m['funnel'].get(tr, {}).get('replied', 0)}</td>"
        + f"<td class=num>{m['funnel'].get(tr, {}).get('positive', 0)}</td></tr>"
        for tr in TRACK_ORDER)
    buttons = "".join(f"<button data-f='{t}'>{t}</button>" for t in ["ALL"] + TRACK_ORDER[:-1])
    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Prospect Scoreboard</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e6e3dc;--card:#fff;--rel:#3b6fd6;--int:#d6793b;--fit:#2f9e6e;--tim:#8b5cf6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe7;--mut:#9b9a95;--line:#2d2c2a;--card:#1d1d1b}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px}} h1{{font-size:22px;margin:0 0 4px}} .sub{{color:var(--mut);font-size:12px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:16px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}} .kpi b{{display:block;font-size:22px}} .kpi span{{color:var(--mut);font-size:12px}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
th,td{{padding:8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{font-size:12px;color:var(--mut);font-weight:600}}
.num{{text-align:right;font-variant-numeric:tabular-nums}} .wrap{{overflow-x:auto;margin:12px 0 24px}}
.bar{{display:inline-block;height:8px;border-radius:4px;margin-right:2px}} .rel{{background:var(--rel)}} .int{{background:var(--int)}} .fit{{background:var(--fit)}} .tim{{background:var(--tim)}}
.bars{{white-space:nowrap}} .chip{{font-size:11px;padding:2px 6px;border-radius:999px;border:1px solid var(--line)}}
.gA{{color:#2f9e6e;font-weight:700}} .gB{{color:#3b6fd6;font-weight:700}} .gC{{color:#d6793b}} .gD{{color:var(--mut)}}
button{{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:999px;padding:4px 10px;margin:2px;cursor:pointer}} button.on{{background:var(--fg);color:var(--bg)}}
a{{color:inherit}} .legend span{{margin-right:12px}}
</style></head><body><main>
<h1>Prospect Scoreboard</h1><div class=sub>Generated {date.today()} · local file, contains personal data, do not publish</div>
<div class=kpis>{kpi_html}</div>
<h2>Tracks</h2><div class=wrap><table><tr><th>Track</th><th class=num>A</th><th class=num>B</th><th class=num>C</th><th class=num>D</th><th class=num>Started</th><th class=num>Replied</th><th class=num>Positive</th></tr>{tg}</table></div>
<h2>Top {len(rows)} prospects</h2>
<div class="sub legend"><span><i class="bar rel" style="width:12px"></i> Relationship /35</span><span><i class="bar int" style="width:12px"></i> Intent /25</span><span><i class="bar fit" style="width:12px"></i> Fit /30</span><span><i class="bar tim" style="width:12px"></i> Timing /10</span></div>
<div>{buttons}</div>
<div class=wrap><table id=t><tr><th>Grade</th><th class=num>Score</th><th>Person</th><th>Track / stage</th><th>R·I·F·T</th><th>Why</th><th>Next best action</th></tr>{''.join(trs)}</table></div>
</main><script>
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
const f=b.dataset.f;document.querySelectorAll('#t tr[data-track]').forEach(r=>r.style.display=(f==='ALL'||r.dataset.track===f)?'':'none')}});
</script></body></html>"""
    p = path("out", "scoreboard.html")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return p


def export_crm(db):
    """Contacts worth a CRM record (VRX CRM / any CRM import)."""
    import csv
    p = path("out", "crm_push.csv")
    rows = db.execute("SELECT * FROM contacts WHERE stage IN ('CONVERSATION','MEETING','PROPOSAL','WON') "
                      "OR (grade='A' AND track IN ('REACTIVATE','ICP','PARTNER','BUILDER'))").fetchall()
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "linkedin_url", "company", "role", "email", "stage", "track", "score", "vertical", "tags", "notes"])
        for r in rows:
            tags = f"source:linkedin-engine,track:{(r['track'] or '').lower()},grade:{r['grade']}"
            if r["vertical"]:
                tags += f",vertical:{r['vertical']}"
            w.writerow([r["name"], full_url(r["key"]), r["company"], r["position"] or r["headline"], r["email"],
                        r["stage"], r["track"], r["score"], r["vertical"], tags, r["next_action"]])
    return p, len(rows)


def dump_json(db):
    return json.dumps(metrics(db), indent=1, default=str)
