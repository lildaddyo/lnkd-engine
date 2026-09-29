"""Import -> score -> plan daily queue -> sync Cowork results/replies."""
import csv
import glob
import re
import json
import os
import random
import shutil
from datetime import date, datetime, timedelta, timezone

from . import classify, ingest, store
from .util import first_name, from_iso, full_url, is_cyrillic, iso, norm_url

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIVE_STAGES = ("REPLIED", "CONVERSATION", "MEETING", "PROPOSAL", "WON", "LOST", "DNC", "NOT_CONNECTED")
AUTO_OPTIONS = ["ICP", "BUILDER", "PARTNER", "NETWORK", "STUDENT"]

TOPIC_TXT = {
    "bg": {"training": "за VR обученията", "event": "за събитието", "ar": "за AR проекта", "vr": "за VR проекта",
           "ai": "за AI", "web": "за сайта", "game": "за играта"},
    "en": {"training": "about VR training", "event": "about the event", "ar": "about the AR project",
           "vr": "about the VR project", "ai": "about AI", "web": "about the website", "game": "about the game"},
}


def path(*p):
    return os.path.join(ROOT, *p)


def load_cfg():
    with open(path("config.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    with open(path("templates.json"), encoding="utf-8") as fh:
        cfg["templates"] = json.load(fh)
    return cfg


def open_db():
    return store.connect(path("data", "engine.db"))


# ------------------------------------------------------------------ import
def do_import(db, cfg, export_path, connections=None, crm=None):
    me, people = ingest.load(export_path, connections, crm)
    now = iso(datetime.now(timezone.utc))
    n_new = 0
    for key, f in people.items():
        row = db.execute("SELECT key, features FROM contacts WHERE key=?", (key,)).fetchone()
        if row:
            old = json.loads(row["features"] or "{}")
            for k in ("referred_by", "lang_override"):  # keep engine-added signals across re-imports
                if old.get(k):
                    f[k] = old[k]
            db.execute("UPDATE contacts SET name=COALESCE(NULLIF(?,''),name), features=?, email=COALESCE(NULLIF(?,''),email), "
                       "company=COALESCE(NULLIF(company,''),?), position=COALESCE(NULLIF(position,''),?), updated_at=? WHERE key=?",
                       (f["name"], json.dumps(f), f.get("email", ""), f.get("conn_company", ""), f.get("conn_position", ""), now, key))
        else:
            n_new += 1
            db.execute("INSERT INTO contacts(key,name,first_name,features,email,company,position,stage,updated_at) "
                       "VALUES(?,?,?,?,?,?,?,'NEW',?)",
                       (key, f["name"], first_name(f["name"]), json.dumps(f), f.get("email", ""),
                        f.get("conn_company", ""), f.get("conn_position", ""), now))
    store.meta_set(db, "me", me)
    has_conn = any("connections" in f.get("sources", []) for f in people.values())
    store.meta_set(db, "has_connections", has_conn)
    if has_conn:  # only 1st-degree connections can receive a normal DM
        for key, f in people.items():
            if "connections" not in f.get("sources", []):
                db.execute("UPDATE contacts SET stage='NOT_CONNECTED' WHERE key=? AND stage='NEW'", (key,))
            else:
                db.execute("UPDATE contacts SET stage='NEW' WHERE key=? AND stage='NOT_CONNECTED'", (key,))
    rescore(db, cfg)
    db.commit()
    return len(people), n_new


def _contact(row):
    c = dict(row)
    c["features"] = json.loads(c["features"] or "{}")
    return c


def pick_lang(c):
    f = c["features"]
    if f.get("lang_override"):
        return f["lang_override"]
    if is_cyrillic(c.get("name")) or (f.get("cyr_share") or 0) > 0.4:
        return "bg"
    if is_cyrillic(c.get("headline") or "") or "bulgaria" in (c.get("location") or "").lower() \
            or "българия" in (c.get("location") or "").lower():
        return "bg"
    if f.get("crm"):
        return "bg"
    if BG_COMPANY.search(c.get("company") or "") or BG_COMPANY.search(c.get("headline") or ""):
        return "bg"
    toks = (c.get("name") or "").split()
    if toks and BG_SURNAME.search(toks[-1]):
        return "bg"  # Cowork confirms against the profile location and may switch
    return "en"


BG_COMPANY = re.compile(r"bulgari|българ|sofia|софия|plovdiv|пловдив|varna|варна|\bE?OOD\b|\bЕ?ООД\b|\bАД\b|\.bg\b|\bBG\b", re.I)
BG_SURNAME = re.compile(r"(ov|ova|ev|eva|ski|ska)$", re.I)


def rescore(db, cfg, keys=None):
    q = "SELECT * FROM contacts" + (" WHERE key IN (%s)" % ",".join("?" * len(keys)) if keys else "")
    for row in db.execute(q, keys or ()).fetchall():
        c = _contact(row)
        s = classify.score(c, cfg)
        track = "DNC" if c["stage"] == "DNC" else s["track"]
        db.execute("UPDATE contacts SET track=?, score=?, grade=?, s_rel=?, s_intent=?, s_fit=?, s_timing=?, fit_known=?, "
                   "seniority=?, function=?, vertical=?, next_action=?, reasons=?, lang=? WHERE key=?",
                   (track, s["score"], s["grade"], s["s_rel"], s["s_intent"], s["s_fit"], s["s_timing"], s["fit_known"],
                    s["seniority"], s["function"], s["vertical"], s["next_action"], s["reasons"], pick_lang(c), c["key"]))


# ------------------------------------------------------------------ render
def render(cfg, c, track, touch, variant, lang):
    t = cfg["templates"].get(track, {}).get(lang, {}).get(str(touch), {})
    tpl = t.get(variant) or t.get("a")
    if not tpl:
        return ""
    f = c["features"]
    s = classify.score(dict(c, manual_track=track), cfg)
    offer = cfg["offers"].get(s["offer_key"], cfg["offers"]["default"])[lang]
    vkey = {"pharma": "pharma", "banking": "banking", "fmcg": "fmcg", "telco": "telco", "retail": "retail"}.get(s["vertical"], "default")
    proof = cfg["proof"][vkey][lang]
    ctx = ""
    last2 = from_iso(f.get("last_two_way_at"))
    if last2 and track in ("REACTIVATE", "WARM") and (datetime.now(timezone.utc) - last2).days > 180:
        topic = TOPIC_TXT[lang].get(f.get("last_topic") or "", "")
        ctx = (f"Последно си писахме през {last2.year} {topic}. " if lang == "bg"
               else f"We last spoke in {last2.year} {topic}. ").replace("  ", " ").replace(" .", ".")
    fn = c.get("first_name") or first_name(c.get("name")) or ""
    sender = cfg["sender"]["first_name_bg" if lang == "bg" else "first_name"]
    msg = tpl.format(first_name=fn, hook="{hook}", context=ctx, proof=proof, offer=offer, sender=sender)
    return " ".join(msg.split())


# ------------------------------------------------------------------ experiments
def variant_stats(db):
    """(track, lang, variant) -> [sent, successes] for touch-1 sequences."""
    stats = {}
    rows = db.execute("SELECT t.key, t.track, t.lang, t.variant, t.sent_at FROM touches t "
                      "WHERE t.kind='message' AND t.touch=1 AND t.status='sent'").fetchall()
    good = {}
    for r in db.execute("SELECT key, sentiment FROM replies").fetchall():
        if r["sentiment"] in ("positive", "neutral", "referral"):
            good[r["key"]] = True
    for r in rows:
        k = (r["track"], r["lang"], r["variant"])
        s = stats.setdefault(k, [0, 0])
        s[0] += 1
        s[1] += 1 if good.get(r["key"]) else 0
    return stats


def choose_variant(cfg, stats, track, lang, rng):
    variants = sorted(cfg["templates"].get(track, {}).get(lang, {}).get("1", {}).keys()) or ["a"]
    best, best_v = -1, variants[0]
    for v in variants:
        n, r = stats.get((track, lang, v), [0, 0])
        sample = rng.betavariate(1 + r, 1 + n - r)
        if sample > best:
            best, best_v = sample, v
    return best_v


# ------------------------------------------------------------------ plan
def send_day_index(db, cfg, d):
    start = store.meta_get(db, "start_date")
    if not start:
        start = d.isoformat()
        store.meta_set(db, "start_date", start)
    s = date.fromisoformat(start)
    days = [s + timedelta(i) for i in range((d - s).days + 1)]
    return max(1, sum(1 for x in days if x.weekday() in cfg["volume"]["send_weekdays"]))


def daily_cap(cfg, idx, rng):
    v = cfg["volume"]
    cap = v["ramp"][0]["cap"]
    for step in v["ramp"]:
        if idx >= step["from_day"]:
            cap = step["cap"]
    if cap >= v["min_daily"]:
        return rng.randint(v["min_daily"], min(v["max_daily"], cap))
    return max(1, int(cap * (1 + rng.uniform(-v["jitter"], v["jitter"]))))


def plan(db, cfg, d, force=False, cap_override=None):
    if d.weekday() not in cfg["volume"]["send_weekdays"] and not force:
        return None, f"{d} is not a send day (config.volume.send_weekdays). Use --force to override."
    rng = random.Random(d.toordinal())
    ds = d.isoformat()
    db.execute("UPDATE touches SET status='expired' WHERE status='planned' AND plan_date<?", (ds,))
    db.execute("DELETE FROM touches WHERE status='planned' AND plan_date=?", (ds,))
    # sequences that ran out without a reply -> NURTURE
    db.execute("UPDATE contacts SET stage='NURTURE', next_due=NULL WHERE stage='IN_SEQUENCE' AND touch>=3 AND next_due<=?", (ds,))

    idx = send_day_index(db, cfg, d)
    cap = cap_override or daily_cap(cfg, idx, rng)
    offsets = cfg["sequence"]["touch_offsets_days"]
    queue = []

    # 1) due follow-ups first (highest yield per message)
    fu_max = int(cap * cfg["volume"]["followup_share_max"])
    for row in db.execute("SELECT * FROM contacts WHERE stage='IN_SEQUENCE' AND touch<? AND next_due<=? "
                          "ORDER BY score DESC", (len(offsets), ds)).fetchall():
        if len(queue) >= fu_max:
            break
        c = _contact(row)
        tr = c["seq_track"] or c["track"]
        queue.append((c, tr, c["touch"] + 1, "a"))

    # 2) new first touches by track quota
    remaining = cap - len(queue)
    cooldown = cfg["sequence"]["cooldown_days"]
    nurture_cut = (d - timedelta(cfg["sequence"]["nurture_after_days"])).isoformat()
    pool = {}
    for row in db.execute("SELECT * FROM contacts WHERE track!='DNC' AND (stage='NEW' OR (stage='NURTURE' AND last_touch_at<?))",
                          (nurture_cut,)).fetchall():
        c = _contact(row)
        f = c["features"]
        lo = from_iso(f.get("last_out_at"))
        if lo and (d - lo.date()).days < cooldown:
            continue
        ia = from_iso(f.get("invite_at"))
        if f.get("invite_dir") == "out" and ia and (d - ia.date()).days < 30 \
                and "connections" not in f.get("sources", []) and not f.get("msgs_in"):
            continue  # invitation probably still pending: can't DM yet
        pri = (c["score"] or 0) + (4 if c["fit_known"] else 0) + rng.uniform(0, 3)
        pool.setdefault(c["track"], []).append((pri, c))
    for tr in pool:
        pool[tr].sort(key=lambda x: -x[0])
    mix = {k: v for k, v in cfg["track_mix"].items() if not k.startswith("_")}
    taken = set()
    stats = variant_stats(db)
    for tr, share in mix.items():
        n = int(round(remaining * share))
        for _, c in pool.get(tr, [])[:n]:
            queue.append((c, tr, 1, None))
            taken.add(c["key"])
    leftovers = sorted((p for tr in pool for p in pool[tr] if p[1]["key"] not in taken), key=lambda x: -x[0])
    for _, c in leftovers:
        if len(queue) >= cap:
            break
        queue.append((c, c["track"], 1, None))
    queue = queue[:cap]

    # 3) render + persist
    out = []
    for i, (c, tr, touch, variant) in enumerate(queue, 1):
        lang = c.get("lang") or pick_lang(c)
        item = {
            "touch_id": f"{ds}-{i:03d}", "profile_url": full_url(c["key"]), "name": c["name"],
            "first_name": c.get("first_name") or first_name(c["name"]), "touch": touch, "track": tr,
            "lang": lang, "score": c["score"], "grade": c["grade"], "why": c["reasons"],
            "known_headline": c.get("headline") or c.get("position") or "",
        }
        if tr == "AUTO" and touch == 1:
            item["variant"] = "a"
            item["options"] = {o: render(cfg, c, o, 1, choose_variant(cfg, stats, o, lang, rng), lang) for o in AUTO_OPTIONS}
            item["message"] = ""
        else:
            item["variant"] = variant or (choose_variant(cfg, stats, tr, lang, rng) if touch == 1 else c.get("variant") or "a")
            item["message"] = render(cfg, c, tr, touch, "a" if touch > 1 else item["variant"], lang)
        db.execute("INSERT INTO touches(id,key,plan_date,touch,track,lang,variant,kind,status,message) "
                   "VALUES(?,?,?,?,?,?,?,'message','planned',?)",
                   (item["touch_id"], c["key"], ds, touch, tr, lang, item["variant"],
                    item["message"] or json.dumps(item.get("options"), ensure_ascii=False)))
        out.append(item)
    db.commit()
    _write_queue(d, out, cap, idx)
    return out, f"{len(out)} messages planned for {ds} (send-day #{idx}, cap {cap})"


def _write_queue(d, items, cap, idx):
    os.makedirs(path("out"), exist_ok=True)
    base = path("out", f"queue_{d.isoformat()}")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump({"date": d.isoformat(), "send_day": idx, "cap": cap, "items": items}, fh, ensure_ascii=False, indent=1)
    with open(base + ".csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["touch_id", "name", "profile_url", "track", "touch", "lang", "variant", "grade", "score", "message"])
        for it in items:
            w.writerow([it["touch_id"], it["name"], it["profile_url"], it["track"], it["touch"], it["lang"],
                        it["variant"], it["grade"], it["score"], it["message"] or "(AUTO: pick from options)"])
    # results template Cowork fills in
    res = path("inbox", f"results_{d.isoformat()}.csv")
    if not os.path.exists(res):
        os.makedirs(path("inbox"), exist_ok=True)
        with open(res, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(RESULT_COLS)
            for it in items:
                w.writerow([it["touch_id"], it["profile_url"], "", "", "", "", "", "", "", "", "", ""])


RESULT_COLS = ["touch_id", "profile_url", "status", "sent_at", "chosen_track", "lang", "final_message",
               "headline", "company", "position", "location", "note"]
REPLY_COLS = ["profile_url", "replied_at", "sentiment", "next_step", "summary", "referred_name", "referred_url"]


# ------------------------------------------------------------------ sync
def sync(db, cfg):
    offsets = cfg["sequence"]["touch_offsets_days"]
    report = {"sent": 0, "skipped": 0, "not_connected": 0, "replies": 0, "referrals": 0, "files": []}
    touched = set()
    done_dir = path("inbox", "processed")
    os.makedirs(done_dir, exist_ok=True)
    for fp in sorted(glob.glob(path("inbox", "results_*.csv"))):
        with open(fp, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        pending = 0
        for r in rows:
            st = (r.get("status") or "").strip().lower()
            if not st:
                pending += 1
                continue
            t = db.execute("SELECT * FROM touches WHERE id=?", (r["touch_id"],)).fetchone()
            if not t or t["status"] not in ("planned", "expired"):
                continue
            key = t["key"]
            touched.add(key)
            prof = {k: (r.get(k) or "").strip() for k in ("headline", "company", "position", "location")}
            sets = ", ".join(f"{k}=COALESCE(NULLIF(?,''),{k})" for k in prof)
            db.execute(f"UPDATE contacts SET {sets} WHERE key=?", (*prof.values(), key))
            if st == "sent":
                sent_at = (r.get("sent_at") or "").strip() or datetime.now(timezone.utc).isoformat()
                sd = (from_iso(sent_at) or datetime.now(timezone.utc)).date()
                n = t["touch"]
                tr = (r.get("chosen_track") or "").strip().upper() or t["track"]
                gap = offsets[n] - offsets[n - 1] if n < len(offsets) else cfg["sequence"]["reply_window_days"]
                db.execute("UPDATE touches SET status='sent', sent_at=?, final_message=?, track=?, "
                           "lang=COALESCE(NULLIF(?,''),lang) WHERE id=?",
                           (sent_at, r.get("final_message", ""), tr, (r.get("lang") or "").strip(), t["id"]))
                db.execute("UPDATE contacts SET stage=CASE WHEN stage IN ('NEW','NURTURE','IN_SEQUENCE') THEN 'IN_SEQUENCE' ELSE stage END, "
                           "touch=?, seq_track=?, variant=CASE WHEN ?=1 THEN ? ELSE variant END, last_touch_at=?, next_due=? WHERE key=?",
                           (n, tr, n, t["variant"], sent_at, (sd + timedelta(gap)).isoformat(), key))
                report["sent"] += 1
            elif st in ("skipped_not_connected", "not_connected"):
                db.execute("UPDATE touches SET status='skipped_not_connected', note=? WHERE id=?", (r.get("note", ""), t["id"]))
                db.execute("UPDATE contacts SET stage='NOT_CONNECTED' WHERE key=?", (key,))
                report["not_connected"] += 1
            else:
                db.execute("UPDATE touches SET status=?, note=? WHERE id=?", (st, r.get("note", ""), t["id"]))
                report["skipped"] += 1
        if pending == 0:
            shutil.move(fp, os.path.join(done_dir, os.path.basename(fp)))
        report["files"].append(os.path.basename(fp) + ("" if pending == 0 else f" ({pending} rows still blank; kept)"))

    for fp in sorted(glob.glob(path("inbox", "replies_*.csv"))):
        with open(fp, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                key = norm_url(r.get("profile_url"))
                if not key:
                    continue
                touched.add(key)
                ref = apply_reply(db, cfg, key, r, report)
                if ref:
                    touched.add(ref)
        shutil.move(fp, os.path.join(done_dir, os.path.basename(fp)))
        report["files"].append(os.path.basename(fp))
    if touched:
        rescore(db, cfg, list(touched))
    db.commit()
    return report


STAGE_BY_STEP = {"meeting": "MEETING", "proposal": "PROPOSAL", "won": "WON", "lost": "LOST"}


def apply_reply(db, cfg, key, r, report):
    sent = (r.get("sentiment") or "neutral").strip().lower()
    step = (r.get("next_step") or "").strip().lower()
    at = (r.get("replied_at") or "").strip() or datetime.now(timezone.utc).isoformat()
    if not db.execute("SELECT 1 FROM contacts WHERE key=?", (key,)).fetchone():
        db.execute("INSERT INTO contacts(key,name,first_name,features,stage) VALUES(?,?,?,?,'NEW')",
                   (key, "", "", json.dumps({"sources": ["reply"]})))
    t = db.execute("SELECT id FROM touches WHERE key=? AND status='sent' ORDER BY sent_at DESC LIMIT 1", (key,)).fetchone()
    db.execute("INSERT INTO replies(key,replied_at,sentiment,summary,next_step,touch_id,referred_name,referred_url) "
               "VALUES(?,?,?,?,?,?,?,?)", (key, at, sent, r.get("summary", ""), step, t["id"] if t else None,
                                          r.get("referred_name", ""), r.get("referred_url", "")))
    report["replies"] += 1
    if sent == "ooo":
        db.execute("UPDATE contacts SET next_due=? WHERE key=?", ((date.today() + timedelta(7)).isoformat(), key))
        return None
    if sent == "dnc":
        stage = "DNC"
    elif step in STAGE_BY_STEP:
        stage = STAGE_BY_STEP[step]
    elif sent == "positive":
        stage = "CONVERSATION"
    elif sent == "negative":
        stage = "LOST"
    else:
        stage = "REPLIED"
    db.execute("UPDATE contacts SET stage=?, next_due=NULL, track=CASE WHEN ?='DNC' THEN 'DNC' ELSE track END WHERE key=?",
               (stage, stage, key))
    ref = norm_url(r.get("referred_url"))
    if ref:
        row = db.execute("SELECT features FROM contacts WHERE key=?", (ref,)).fetchone()
        if row:
            f = json.loads(row["features"] or "{}")
            f["referred_by"] = key
            db.execute("UPDATE contacts SET features=? WHERE key=?", (json.dumps(f), ref))
        else:
            nm = r.get("referred_name", "")
            db.execute("INSERT INTO contacts(key,name,first_name,features,stage) VALUES(?,?,?,?,'NEW')",
                       (ref, nm, first_name(nm), json.dumps({"sources": ["referral"], "referred_by": key})))
        report["referrals"] += 1
    return ref


def mark(db, cfg, url, stage=None, track=None, lang=None):
    key = norm_url(url)
    if not db.execute("SELECT 1 FROM contacts WHERE key=?", (key,)).fetchone():
        return False
    if stage:
        db.execute("UPDATE contacts SET stage=? WHERE key=?", (stage.upper(), key))
    if track:
        db.execute("UPDATE contacts SET manual_track=? WHERE key=?", (track.upper(), key))
    if lang:
        f = json.loads(db.execute("SELECT features FROM contacts WHERE key=?", (key,)).fetchone()["features"] or "{}")
        f["lang_override"] = lang
        db.execute("UPDATE contacts SET features=? WHERE key=?", (json.dumps(f), key))
    rescore(db, cfg, [key])
    db.commit()
    return True
