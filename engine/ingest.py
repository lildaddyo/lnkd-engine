"""Turn a LinkedIn data export (+ optional Connections.csv / CRM csv) into per-person signals."""
import collections
import csv
import io
import os
import re
import zipfile

from .util import (any_re, clean_html, first_name, is_cyrillic, iso, names_match,
                   name_key_tokens, norm_url, parse_dt)

csv.field_size_limit(1 << 30)

# ---- signal vocab (BG + EN) --------------------------------------------------
RX = {
    "meeting": any_re([r"\bсреща", r"\bmeeting", r"\bcall\b", r"обаждан", r"да се чуем", r"да се видим",
                       r"calendly", r"\bzoom\b", r"\bteams\b", r"google meet", r"кафе"]),
    "price": any_re([r"\bцен[аи]", r"оферт", r"бюджет", r"\bprice", r"pricing", r"\bquote", r"proposal",
                     r"\boffer\b", r"фактур", r"invoice", r"договор", r"contract"]),
    "xr": any_re([r"\bVR\b", r"\bAR\b", r"\bXR\b", r"виртуалн", r"добавена реалност", r"metaverse",
                  r"метавселен", r"\bquest\b", r"очила", r"360", r"immersive"]),
    "ai": any_re([r"\bAI\b", r"\bИИ\b", r"изкуствен интелект", r"chatgpt", r"\bgpt", r"claude", r"агент", r"\bagent"]),
    "positive": any_re([r"интересно", r"звучи (добре|супер|страхотно)", r"с удоволствие", r"ще се радвам",
                        r"sounds (good|great)", r"interested", r"let'?s (talk|do|schedule)", r"would love",
                        r"супер", r"чудесно", r"great idea"]),
    "later": any_re([r"ще (ви|те) имам предвид", r"keep (you )?in mind", r"не в момента", r"not right now",
                     r"по-късно", r"later this year", r"следващата година", r"next year"]),
    "negative": any_re([r"не се интересува", r"не ни интересува", r"not interested", r"unsubscribe",
                        r"моля,? не ми пишете", r"stop messaging", r"remove me", r"не желая", r"no thanks",
                        r"не,? благодаря"]),
    "student": any_re([r"студент", r"\bstudent", r"университет", r"university", r"\bУНСС\b", r"\bНБУ\b",
                       r"семест", r"\bintern", r"стажант", r"\bстаж", r"дипломн", r"бакалавър", r"магист",
                       r"bachelor", r"master'?s", r"курсова", r"изпит", r"\bexam"]),
    "job": any_re([r"\bCV\b", r"резюме", r"търся работа", r"looking for (a )?job", r"кандидатств",
                   r"open to work", r"позицията"]),
    "pitch": any_re([r"our (platform|agency|company|team|services)", r"we help", r"we (are|offer)",
                     r"webinar", r"уебинар", r"предлагаме", r"нашата (компания|платформа|агенция)",
                     r"book a (call|demo)", r"free (trial|audit)", r"lead generation", r"outsourc"]),
    "phone": re.compile(r"(\+?359|0)8[789]\d[\s-]?\d{3}[\s-]?\d{3}"),
}

TOPICS = [
    ("training", any_re([r"обучени", r"training", r"onboarding", r"онбординг"])),
    ("event", any_re([r"събити", r"\bevent", r"активаци", r"activation", r"изложени", r"конферен"])),
    ("ar", any_re([r"\bAR\b", r"добавена реалност", r"webar"])),
    ("vr", any_re([r"\bVR\b", r"виртуална реалност", r"очила", r"quest"])),
    ("ai", RX["ai"]),
    ("web", any_re([r"уебсайт", r"\bсайт", r"website", r"landing", r"приложение", r"\bapp\b"])),
    ("game", any_re([r"\bигр", r"\bgame", r"quiz", r"куиз", r"викторин"])),
]


class Export:
    """Reads CSVs from a LinkedIn export .zip or folder (and loose CSVs in data/)."""

    def __init__(self, path):
        self.path = path
        self.zip = zipfile.ZipFile(path) if path and path.lower().endswith(".zip") else None

    def _names(self):
        if self.zip:
            return self.zip.namelist()
        out = []
        for root, _, files in os.walk(self.path):
            for f in files:
                out.append(os.path.relpath(os.path.join(root, f), self.path))
        return out

    def find(self, basename):
        for n in self._names():
            if os.path.basename(n).lower() == basename.lower():
                return n
        return None

    def text(self, basename):
        n = self.find(basename)
        if not n:
            return None
        if self.zip:
            raw = self.zip.read(n)
        else:
            with open(os.path.join(self.path, n), "rb") as fh:
                raw = fh.read()
        return raw.decode("utf-8-sig", errors="replace")

    def rows(self, basename, header_starts=None):
        t = self.text(basename)
        if t is None:
            return []
        if header_starts:  # Connections.csv has "Notes:" lines above the header
            i = t.find(header_starts)
            if i > 0:
                t = t[i:]
        return list(csv.DictReader(io.StringIO(t)))


def _blank():
    return {
        "name": "", "sources": set(), "msgs_in": 0, "msgs_out": 0, "msgs_out_template": 0,
        "convs": 0, "convs_two_way": 0, "group_only": True, "they_initiated": 0,
        "first_at": None, "last_at": None, "last_in_at": None, "last_out_at": None, "last_two_way_at": None,
        "pitch_inbound": False, "spam": False, "hits": collections.Counter(), "negative_last": False,
        "cyr_chars": 0, "chars": 0, "topics": collections.Counter(), "last_topic": None,
        "invite_dir": None, "invite_at": None, "endorsed_me": 0, "i_follow": False,
        "connected_on": None, "conn_company": "", "conn_position": "", "email": "",
        "crm": None,
    }


def _mx(a, b):
    return b if a is None or (b and b > a) else a


def _mn(a, b):
    return b if a is None or (b and b < a) else a


def detect_me(msg_rows, inv_rows):
    for r in inv_rows:
        if r.get("Direction") == "OUTGOING" and r.get("inviterProfileUrl"):
            return norm_url(r["inviterProfileUrl"])
    c = collections.Counter(norm_url(r.get("SENDER PROFILE URL")) for r in msg_rows)
    c.pop("", None)
    return c.most_common(1)[0][0] if c else ""


def template_keys(msg_rows, me):
    """Outbound bodies sent near-identically to many people (mass campaigns)."""
    cnt = collections.Counter()
    for r in msg_rows:
        if norm_url(r.get("SENDER PROFILE URL")) != me:
            continue
        cnt[_tkey(r)] += 1
    return {k for k, v in cnt.items() if v >= 8 and k}


def _tkey(r):
    body = clean_html(r.get("CONTENT", "")).lower()
    to = (r.get("TO") or "").split(",")[0]
    fn = first_name(to).lower()
    if fn:
        body = body.replace(fn, "{n}")
    body = re.sub(r"\d+", "#", body)
    return body[:160]


def load(export_path, connections_path=None, crm_path=None):
    ex = Export(export_path) if export_path else None
    msgs = ex.rows("messages.csv") if ex else []
    invs = ex.rows("Invitations.csv") if ex else []
    me = detect_me(msgs, invs)
    people = collections.defaultdict(_blank)
    tmpl = template_keys(msgs, me)

    # ---- messages --------------------------------------------------------
    convs = collections.defaultdict(list)
    for r in msgs:
        convs[r.get("CONVERSATION ID")].append(r)
    for cid, rows in convs.items():
        rows.sort(key=lambda r: r.get("DATE") or "")
        parts = set()
        for r in rows:
            s = norm_url(r.get("SENDER PROFILE URL"))
            if s:
                parts.add(s)
            for u in (r.get("RECIPIENT PROFILE URLS") or "").split(","):
                if norm_url(u):
                    parts.add(norm_url(u))
        parts.discard(me)
        if not parts:
            continue
        is_group = len(parts) > 1
        title = (rows[0].get("CONVERSATION TITLE") or "").strip()
        spam = any((r.get("FOLDER") or "").upper() == "SPAM" for r in rows)
        for p in parts:
            f = people[p]
            f["sources"].add("messages")
            f["convs"] += 1
            if not is_group:
                f["group_only"] = False
            ins = [r for r in rows if norm_url(r.get("SENDER PROFILE URL")) == p]
            outs = [r for r in rows if norm_url(r.get("SENDER PROFILE URL")) == me]
            if ins and not f["name"]:
                f["name"] = ins[0].get("FROM", "")
            if not f["name"] and not is_group and outs:
                f["name"] = (outs[0].get("TO") or "").split(",")[0]
            f["spam"] = f["spam"] or spam
            if not is_group and rows and norm_url(rows[0].get("SENDER PROFILE URL")) == p:
                f["they_initiated"] += 1
            if ins and outs and not is_group:
                f["convs_two_way"] += 1
                f["last_two_way_at"] = _mx(f["last_two_way_at"], parse_dt(rows[-1].get("DATE")))
            if ins and not outs and (title or len(clean_html(ins[0].get("CONTENT", ""))) > 350) \
                    and RX["pitch"].search(clean_html(ins[0].get("CONTENT", ""))):
                f["pitch_inbound"] = True
            conv_text = []
            for r in rows:
                d = parse_dt(r.get("DATE"))
                f["first_at"] = _mn(f["first_at"], d)
                f["last_at"] = _mx(f["last_at"], d)
                body = clean_html(r.get("CONTENT", ""))
                sender = norm_url(r.get("SENDER PROFILE URL"))
                if sender == p:
                    f["msgs_in"] += 1
                    f["last_in_at"] = _mx(f["last_in_at"], d)
                    for k in ("meeting", "price", "xr", "ai", "positive", "later", "student", "job"):
                        if RX[k].search(body):
                            f["hits"][k] += 1
                    if RX["phone"].search(body):
                        f["hits"]["phone"] += 1
                elif sender == me and not is_group:
                    if _tkey(r) in tmpl:
                        f["msgs_out_template"] += 1
                    else:
                        f["msgs_out"] += 1
                        if RX["student"].search(body):
                            f["hits"]["student_out"] += 1
                    f["last_out_at"] = _mx(f["last_out_at"], d)
                conv_text.append(body)
                f["chars"] += len(body)
                f["cyr_chars"] += sum(1 for c in body if "а" <= c.lower() <= "я")
            if ins and outs and not is_group:
                joined = " ".join(conv_text)
                for label, rx in TOPICS:
                    if rx.search(joined):
                        f["topics"][label] += 1
                        f["last_topic"] = label
            if ins:
                last_in = clean_html(ins[-1].get("CONTENT", ""))
                f["negative_last"] = bool(RX["negative"].search(last_in))

    # ---- invitations -----------------------------------------------------
    for r in invs:
        out = r.get("Direction") == "OUTGOING"
        k = norm_url(r.get("inviteeProfileUrl") if out else r.get("inviterProfileUrl"))
        if not k or k == me:
            continue
        f = people[k]
        f["sources"].add("invitations")
        f["name"] = f["name"] or (r.get("To") if out else r.get("From")) or ""
        f["invite_dir"] = "out" if out else "in"
        f["invite_at"] = parse_dt(r.get("Sent At"))

    # ---- endorsements (they vouched for you) -----------------------------
    by_name = collections.defaultdict(list)
    for k, f in people.items():
        toks = name_key_tokens(f["name"])
        if toks:
            by_name[toks[0]].append(k)
    for r in (ex.rows("Endorsement_Received_Info.csv") if ex else []):
        k = norm_url(r.get("Endorser Public Url"))
        if not k:
            continue
        f = people[k]
        f["sources"].add("endorsements")
        f["name"] = f["name"] or f"{r.get('Endorser First Name','')} {r.get('Endorser Last Name','')}".strip()
        f["endorsed_me"] += 1

    # ---- people you follow (name-only; enrich existing contacts) ----------
    for r in (ex.rows("Member_Follows_188649616.csv") if ex else []) or _glob_rows(ex, "Member_Follows"):
        if r.get("Status") != "Active":
            continue
        nm = r.get("FullName", "")
        toks = name_key_tokens(nm)
        for k in by_name.get(toks[0] if toks else "", []):
            if names_match(people[k]["name"], nm):
                people[k]["i_follow"] = True

    # ---- Connections.csv (best source: company + position) ---------------
    conn_rows = []
    if connections_path and os.path.exists(connections_path):
        with open(connections_path, encoding="utf-8-sig") as fh:
            t = fh.read()
        i = t.find("First Name")
        conn_rows = list(csv.DictReader(io.StringIO(t[i:] if i >= 0 else t)))
    elif ex:
        conn_rows = ex.rows("Connections.csv", header_starts="First Name")
    for r in conn_rows:
        k = norm_url(r.get("URL"))
        if not k:
            continue
        f = people[k]
        f["sources"].add("connections")
        f["name"] = f"{r.get('First Name','')} {r.get('Last Name','')}".strip() or f["name"]
        f["connected_on"] = parse_dt(r.get("Connected On"))
        f["conn_company"] = r.get("Company", "") or ""
        f["conn_position"] = r.get("Position", "") or ""
        f["email"] = r.get("Email Address", "") or ""

    # ---- CRM warm list ---------------------------------------------------
    if crm_path and os.path.exists(crm_path):
        with open(crm_path, encoding="utf-8-sig") as fh:
            crm = list(csv.DictReader(fh))
        idx = collections.defaultdict(list)
        for k, f in people.items():
            toks = name_key_tokens(f["name"])
            if toks:
                idx[toks[0]].append(k)
        for c in crm:
            k = norm_url(c.get("linkedin_url"))
            targets = [k] if k else []
            if not targets:
                toks = name_key_tokens(c.get("name"))
                targets = [p for p in idx.get(toks[0] if toks else "", []) if names_match(people[p]["name"], c.get("name"))]
            for t in targets[:1]:
                people[t]["crm"] = {x: c.get(x, "") for x in ("tier", "vertical", "company", "role")}
                people[t]["sources"].add("crm")

    people.pop(me, None)
    people.pop("", None)
    return me, {k: _finalize(f) for k, f in people.items()}


def _glob_rows(ex, prefix):
    if not ex:
        return []
    for n in ex._names():
        b = os.path.basename(n)
        if b.startswith(prefix) and b.endswith(".csv"):
            return ex.rows(b)
    return []


def _finalize(f):
    out = dict(f)
    out["sources"] = sorted(f["sources"])
    out["hits"] = dict(f["hits"])
    out["topics"] = dict(f["topics"])
    out["cyr_share"] = round(f["cyr_chars"] / f["chars"], 2) if f["chars"] else None
    for k in ("first_at", "last_at", "last_in_at", "last_out_at", "last_two_way_at", "invite_at", "connected_on"):
        out[k] = iso(f[k])
    out["name_cyr"] = is_cyrillic(f["name"])
    return out
