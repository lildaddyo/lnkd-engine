"""Opportunity + campaign dashboard (out/dashboard.html) and CSV exports (out/opportunities/*.csv).

Self-contained, no network, no CDN. Reads only data/engine.db. Campaign panels are empty until sends are logged.
"""
import collections
import csv
import json
import os
import re
from datetime import datetime, timezone

from . import core, segments

HERE = os.path.dirname(os.path.abspath(__file__))
TOP_N = 400
COMPANY_STOP = {"freelance", "self employed", "selfemployed", "confidential", "stealth", "nda", ""}
CORP_SUFFIX = re.compile(r"\b(ltd|eood|ood|ad|gmbh|inc|llc|bulgaria|group|ead)\b")


def _months(iso_s):
    if not iso_s:
        return None
    try:
        d = datetime.fromisoformat(iso_s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days / 30.4
    except ValueError:
        return None


def _warmth(f):
    mo = _months(f.get("last_two_way_at"))
    if mo is None:
        return "inbound/invite only" if f.get("invite_dir") else "no conversation"
    return "live (<3m)" if mo < 3 else "recent (3-12m)" if mo < 12 else "dormant (1y+)"


def contacts(db):
    """Every contact that is not do-not-contact, as flat dicts, best opportunity first."""
    out = []
    for r in db.execute("SELECT * FROM contacts WHERE track!='DNC' AND stage!='DNC' AND segment IS NOT NULL"):
        f = json.loads(r["features"] or "{}")
        out.append({
            "name": r["name"] or "", "linkedin": "https://www." + r["key"], "company": r["company"] or "",
            "position": r["position"] or "", "lang": r["lang"], "engine_track": r["track"], "engine_grade": r["grade"],
            "engine_score": r["score"], "stage": r["stage"], "segment": r["segment"], "tier": r["opp_tier"],
            "opp_score": r["opp_score"], "primary_stream": r["stream"], "secondary": r["stream2"], "first_offer": r["offer"],
            "value": r["value"], "vertical": segments.VERT_LABEL.get(r["vertical"], ""), "warmth": _warmth(f),
            "two_way_threads": f.get("convs_two_way", 0), "topics": ",".join((f.get("topics") or {}).keys()),
            "seniority": r["seniority"] or "", "crm": (f.get("crm") or {}).get("tier", ""),
        })
    out.sort(key=lambda x: (-x["opp_score"], x["name"]))
    return out


def companies(rows):
    comp = collections.defaultdict(list)
    for o in rows:
        k = CORP_SUFFIX.sub("", re.sub(r"[^a-zа-я0-9 ]", "", o["company"].lower())).strip()
        if k not in COMPANY_STOP:
            comp[k].append(o)
    res = []
    for v in comp.values():
        top = v[0]
        segs = collections.Counter(x["segment"] for x in v)
        res.append({
            "company": top["company"], "contacts": len(v), "best_contact": top["name"], "best_position": top["position"],
            "best_linkedin": top["linkedin"], "best_score": top["opp_score"], "top_segment": segs.most_common(1)[0][0],
            "buyers": sum(1 for x in v if x["segment"] in ("CORPORATE_BUYER", "CLIENT_PAST")),
            "senior_contacts": sum(1 for x in v if x["seniority"] in ("c_level", "director")),
            "warm_contacts": sum(1 for x in v if x["warmth"].startswith(("live", "recent"))),
            "vertical": next((x["vertical"] for x in v if x["vertical"]), ""), "primary_stream": top["primary_stream"],
            "account_score": min(100, top["opp_score"] + 3 * min(len(v) - 1, 6)),
        })
    res.sort(key=lambda x: (-x["account_score"], -x["contacts"]))
    return res


def _count(it):
    return dict(collections.Counter(it))


def campaign(db):
    q = lambda sql: [dict(r) for r in db.execute(sql)]
    ts = {r["status"]: r["n"] for r in q("SELECT status, COUNT(*) n FROM touches GROUP BY status")}
    return {
        "stages": {r["stage"]: r["n"] for r in q("SELECT stage, COUNT(*) n FROM contacts GROUP BY stage")},
        "touch_status": ts, "empty": not ts,
        "by_track": q("SELECT track, COUNT(*) planned, SUM(status='sent') sent FROM touches GROUP BY track"),
        "by_variant": q("SELECT track, lang, variant, SUM(status='sent') sent FROM touches GROUP BY track, lang, variant"),
        "replies": q("SELECT sentiment, COUNT(*) n FROM replies GROUP BY sentiment"),
        "daily": q("SELECT plan_date d, COUNT(*) planned, SUM(status='sent') sent FROM touches GROUP BY plan_date ORDER BY plan_date"),
    }


def crm_review(db):
    """CRM rows that matched a LinkedIn contact by name only, without a company or URL to back it up.
    To confirm one, paste the contact's LinkedIn URL into that row's linkedin_url in data/crm_warm.csv and re-import."""
    out = []
    for r in db.execute("SELECT name, company, position, key, features FROM contacts WHERE features LIKE '%crm_candidates%'"):
        for cand in json.loads(r["features"]).get("crm_candidates", []):
            out.append({"linkedin_name": r["name"], "linkedin_company": r["company"] or "", "linkedin_position": r["position"] or "",
                        "linkedin_url": "https://www." + r["key"], "crm_name": cand["name"], "crm_company": cand["company"],
                        "crm_role": cand["role"], "crm_tier": cand["tier"]})
    out.sort(key=lambda x: (x["crm_name"], x["linkedin_name"]))
    return out


def analytics(db):
    C = contacts(db)
    p12 = [c for c in C if c["tier"] in ("P1", "P2")]
    other = [c for c in C if c["segment"] == "OTHER"]
    words = collections.Counter(w for c in other for w in re.findall(r"[a-zа-я]{4,}", c["position"].lower()))
    excluded = db.execute("SELECT COUNT(*) FROM contacts WHERE track='DNC' OR stage='DNC'").fetchone()[0]
    return {
        "total": len(C), "excluded": {"do-not-contact / never-contact": excluded},
        "tiers": _count(c["tier"] for c in C),
        "seg_tier": {s: _count(c["tier"] for c in C if c["segment"] == s) for s in sorted({c["segment"] for c in C})},
        "stream_tier": {s: _count(c["tier"] for c in C if c["primary_stream"] == s) for s in segments.STREAMS},
        "vertical_p12": _count(c["vertical"] or "No clear vertical" for c in p12),
        "warmth_p12": _count(c["warmth"] for c in p12),
        "value_p12": _count(c["value"] for c in p12),
        "other_words": words.most_common(40), "other_total": len(other), "no_company": sum(1 for c in C if not c["company"]),
        "other_sample": [{"name": c["name"], "position": c["position"], "company": c["company"]} for c in other[:25]],
        "campaign": campaign(db),
        "reactivate": [c for c in p12 if c["warmth"].startswith("dormant") and c["two_way_threads"]][:60],
        "top": p12[:TOP_N], "companies": companies(C)[:200], "streams": segments.STREAMS,
        "crm_review": crm_review(db), "labels": segments.SEGMENT_LABELS, "crm_clients": sum(1 for c in C if c["segment"] == "CLIENT_PAST"),
    }


def build(db, cfg=None):
    """Write out/dashboard.html; return its path."""
    data = analytics(db)
    with open(os.path.join(HERE, "dashboard.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = core.path("out", "dashboard.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(tpl.replace("__DATA__", payload))
    return out


def export_csv(db):
    """out/opportunities/: all_contacts_scored.csv, target_companies.csv, one seg_<segment>.csv each. Returns (dir, n)."""
    d = core.path("out", "opportunities")
    os.makedirs(d, exist_ok=True)
    rows = contacts(db)

    def write(name, data):
        if not data:
            return
        with open(os.path.join(d, name), "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    write("all_contacts_scored.csv", rows)
    write("target_companies.csv", companies(rows))
    write("crm_review.csv", crm_review(db))
    for s in sorted({r["segment"] for r in rows}):
        write(f"seg_{s.lower()}.csv", [r for r in rows if r["segment"] == s])
    return d, len(rows)
