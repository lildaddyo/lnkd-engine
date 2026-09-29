"""Prospect scoreboard: Relationship + Intent + Fit + Timing = 0..100, then a track.

Why these four axes (see PLAYBOOK.md §3):
  Relationship: warm/dormant ties reply far more than cold ones (Levin, Walter & Murnighan 2011).
  Intent: explicit buying language in past threads is the strongest predictor we have.
  Fit: ICP match on seniority x function x vertical (classic two-axis fit/engagement lead scoring).
  Timing: dormant 1-5y ties are the sweet spot; very recent ties are already "live".
"""
from datetime import datetime, timezone

from .util import any_re, from_iso

SENIORITY = [
    ("c_level", 10, any_re([r"\bCEO\b", r"\bCMO\b", r"\bCOO\b", r"\bCTO\b", r"\bCHRO\b", r"\bCFO\b", r"chief",
                            r"founder", r"co-?founder", r"owner", r"собственик", r"управител", r"основател",
                            r"president", r"managing director", r"изпълнителен директор", r"general manager"])),
    ("director", 9, any_re([r"director", r"директор", r"\bhead\b", r"\bVP\b", r"vice president", r"ръководител",
                            r"country manager", r"partner\b"])),
    ("manager", 7, any_re([r"manager", r"мениджър", r"\blead\b", r"lead\b", r"началник", r"brand manager",
                           r"product manager", r"team lead"])),
    ("specialist", 3, any_re([r"specialist", r"специалист", r"expert", r"експерт", r"coordinator",
                              r"координатор", r"executive", r"associate", r"analyst", r"консултант", r"consultant"])),
]

FUNCTION = [
    ("hr", 10, any_re([r"\bHR\b", r"human resources", r"employee experience", r"culture", r"engagement",
                       r"internal comm", r"вътрешни комуникации", r"talent development", r"people\b", r"човешки ресурси", r"talent", r"people (&|and|ops|partner)",
                       r"L&D", r"learning", r"training", r"обучени", r"employer brand", r"работодателска марка",
                       r"onboarding", r"развитие на персонал"])),
    ("marketing", 10, any_re([r"marketing", r"маркетинг", r"\bbrand", r"бранд", r"марка", r"communications",
                              r"комуникаци", r"\bPR\b", r"digital", r"дигитал", r"trade marketing", r"\bCRM\b",
                              r"content", r"social media"])),
    ("events", 9, any_re([r"event", r"събити", r"experiential", r"activation", r"активаци", r"sponsorship"])),
    ("innovation", 8, any_re([r"innovation", r"иновац", r"transformation", r"трансформац", r"\bR&D\b",
                              r"emerging tech", r"\bXR\b", r"\bVR\b", r"\bAI\b"])),
    ("sales", 6, any_re([r"\bsales", r"продажб", r"business development", r"бизнес развитие", r"key account",
                         r"commercial", r"търговск"])),
    ("medical", 6, any_re([r"medical", r"медицин", r"\bMSL\b", r"product manager", r"продуктов мениджър"])),
]

VERTICAL = [
    ("pharma", 10, any_re([r"pharma", r"фарма", r"zentiva", r"recordati", r"novartis", r"sanofi", r"bayer",
                           r"pfizer", r"roche", r"astra ?zeneca", r"\bGSK\b", r"merck", r"novo nordisk", r"teva",
                           r"sopharma", r"софарма", r"actavis", r"servier", r"abbvie", r"haleon", r"janssen",
                           r"boehringer", r"lilly", r"amgen", r"takeda", r"stada", r"krka", r"gedeon", r"berlin-chemie",
                           r"валентис", r"valentis", r"medical", r"health"])),
    ("banking", 9, any_re([r"\bbank", r"банк", r"postbank", r"пощенска", r"\bUBB\b", r"\bОББ\b", r"\bDSK\b",
                           r"\bДСК\b", r"unicredit", r"fibank", r"procredit", r"insurance", r"застрах", r"allianz",
                           r"eurobank", r"raiffeisen", r"generali", r"\bDZI\b", r"\bДЗИ\b", r"fintech", r"leasing"])),
    ("fmcg", 9, any_re([r"coca", r"pepsi", r"unilever", r"nestl", r"procter", r"\bP&G\b", r"heineken",
                        r"carlsberg", r"kamenitza", r"каменица", r"ferrero", r"mondelez", r"\bJTI\b", r"philip morris",
                        r"\bPMI\b", r"british american", r"\bBAT\b", r"red bull", r"loreal", r"l'or[ée]al",
                        r"danone", r"mars\b", r"diageo", r"fmcg"])),
    ("telco", 8, any_re([r"vivacom", r"виваком", r"\bA1\b", r"yettel", r"telenor", r"теленор", r"telecom"])),
    ("retail", 7, any_re([r"lidl", r"kaufland", r"billa", r"decathlon", r"ikea", r"technopolis", r"технополис",
                          r"retail", r"ритейл", r"e-?commerce", r"shop"])),
    ("auto", 7, any_re([r"automotive", r"\bBMW\b", r"mercedes", r"toyota", r"porsche", r"volkswagen", r"renault",
                        r"hyundai", r"auto"])),
    ("corporate", 6, any_re([r"\bEY\b", r"deloitte", r"\bPwC\b", r"\bKPMG\b", r"accenture", r"\bIBM\b",
                             r"microsoft", r"\bSAP\b", r"vmware", r"playtech", r"sensata", r"energy", r"енерг"])),
]

STUDENT_RX = any_re([r"\bstudent", r"студент", r"undergraduate", r"\bintern\b", r"\binterns\b", r"internship",
                     r"стажант", r"\bстаж\b", r"trainee", r"graduate (trainee|program|programme)", r"\bgraduate\b",
                     r"early career", r"bachelor'?s? (student|candidate)", r"master'?s? (student|candidate)",
                     r"phd (student|candidate)", r"\bclass of 20", r"freshman", r"sophomore", r"ученик", r"aspiring",
                     r"\bjunior\b", r"младши", r"\bassistant\b", r"асистент", r"apprentice"])
EMPLOYED_RX = any_re([r"\bmanager", r"director", r"\bhead\b", r"founder", r"\bceo\b", r"мениджър", r"директор",
                      r"executive assistant to", r"professor", r"assistant professor", r"teaching assistant"])
AGENCY_RX = any_re([r"agency", r"агенция", r"\bstudio\b", r"студио", r"creative", r"production", r"продукция",
                    r"продуцент", r"producer", r"communications group", r"media group", r"freelance",
                    r"фрийланс", r"ogilvy", r"havas", r"publicis", r"mccann", r"saatchi", r"wunderman",
                    r"\bBBDO\b", r"\bDDB\b", r"leo burnett", r"grey\b", r"\bTBWA\b", r"dentsu", r"\bM3\b"])
FOUNDER_RX = any_re([r"founder", r"co-?founder", r"основател", r"owner", r"собственик", r"управител",
                     r"\bCEO\b", r"startup", r"стартъп", r"entrepreneur", r"предприемач", r"indie hacker"])
RECRUITER_RX = any_re([r"recruit", r"рекрут", r"head ?hunter", r"talent acquisition", r"sourcer", r"подбор на персонал"])
TECH_IC_RX = any_re([r"developer", r"engineer", r"програмист", r"инженер", r"software", r"designer", r"дизайнер",
                     r"artist", r"3d", r"unity", r"unreal"])

TRACKS = ["DNC", "REACTIVATE", "WARM", "ICP", "BUILDER", "PARTNER", "STUDENT", "NETWORK", "AUTO"]

NEXT_ACTION = {
    "REACTIVATE": "Reactivate: resume where you left off ({topic}), show what's new, then offer {offer}",
    "WARM": "Reconnect as a peer ({topic}); give first, then ask who in their world needs {offer}",
    "ICP": "Relevance-first cold open on {offer} with a {vertical} proof point; interest CTA",
    "BUILDER": "Founder track: AI-native build in weeks; ask what's stuck on their roadmap",
    "PARTNER": "Agency partner track: white-label XR/AI production, partner pricing, referral loop",
    "STUDENT": "Non-sales: BrainTube beta tester, talent pool / internships, campus referrals",
    "NETWORK": "Give-first reconnect, then a specific referral ask on touch 2 (referred leads are worth more)",
    "AUTO": "Unknown profile: Cowork reads the headline at send time and picks the track",
    "DNC": "Do not contact",
}


def _match(table, text):
    for label, pts, rx in table:
        if text and rx.search(text):
            return label, pts
    return None, 0


def _age_days(iso_s, now):
    d = from_iso(iso_s)
    return (now - d).days if d else None


def profile_text(c):
    return " | ".join(x for x in (c.get("headline"), c.get("position"), c.get("company")) if x)


def score(c, cfg, now=None):
    """c: contact dict with features (parsed) + profile fields. Returns scoring dict."""
    now = now or datetime.now(timezone.utc)
    f = c["features"]
    h = f.get("hits", {})
    crm = f.get("crm") or {}
    reasons = []
    prof = profile_text(c)
    if crm:
        prof = prof or f"{crm.get('role','')} | {crm.get('company','')}"

    # ---------------- Relationship (0-35) ----------------
    rel = 0
    if f.get("convs_two_way"):
        rel += 12 + min(8, 2 * (f["convs_two_way"] - 1))
        reasons.append(f"{f['convs_two_way']} two-way thread(s)")
    rel += min(6, f.get("msgs_in", 0) // 3)
    if f.get("they_initiated") and not f.get("pitch_inbound"):
        rel += 3
        reasons.append("they reached out first")
    if f.get("endorsed_me"):
        rel += min(4, 2 + f["endorsed_me"] // 3)
        reasons.append(f"endorsed you x{f['endorsed_me']}")
    if f.get("invite_dir") == "in":
        rel += 2
        reasons.append("they invited you")
    if f.get("i_follow"):
        rel += 2
    con = _age_days(f.get("connected_on"), now)
    if con is not None and con < 90:
        rel += 6
        reasons.append("connected recently")
    elif con is not None and con < 365:
        rel += 3
    if h.get("phone"):
        rel += 3
        reasons.append("shared a phone number")
    if f.get("referred_by"):
        rel += 10
        reasons.append("warm referral")
    tier = (crm.get("tier") or "").lower()
    if "past-buyer" in tier:
        rel += 15
        reasons.append("CRM past buyer")
    elif "dormant" in tier:
        rel += 12
        reasons.append("CRM dormant client")
    elif "channel" in tier:
        rel += 6
    rel = min(35, rel)

    # ---------------- Intent (0-25) ----------------
    intent = 0
    if h.get("price"):
        intent += 8
        reasons.append("talked price/offer/contract")
    if h.get("meeting"):
        intent += 6
        reasons.append("talked about meeting")
    if h.get("xr"):
        intent += 4
    if h.get("ai"):
        intent += 2
    if h.get("positive"):
        intent += 4
    if h.get("later"):
        intent += 2
        reasons.append("said 'keep in mind / later'")
    intent = min(25, intent)

    # ---------------- Fit (0-30) ----------------
    sen, s_pts = _match(SENIORITY, prof)
    fun, f_pts = _match(FUNCTION, prof)
    ver, v_pts = _match(VERTICAL, prof + " " + (crm.get("vertical") or ""))
    student = bool(STUDENT_RX.search(prof)) and not EMPLOYED_RX.search(prof)
    if not prof:
        student = bool(h.get("student", 0) + h.get("student_out", 0) >= 2)
    fit_known = bool(prof)
    if fit_known:
        fit = s_pts + f_pts + v_pts
        if student:
            fit = 0
        if RECRUITER_RX.search(prof):
            fun, fit = "recruiting", max(0, fit - 8)
    else:
        fit = 10  # neutral prior until the headline is known
    fit = min(30, fit)

    # ---------------- Timing (0-10) ----------------
    last2 = _age_days(f.get("last_two_way_at"), now)
    if last2 is None:
        timing = 3
    elif last2 < 90:
        timing = 4
    elif last2 < 365:
        timing = 8
    elif last2 < 5 * 365:
        timing = 10
        reasons.append(f"dormant tie ({last2 // 365}y)")
    else:
        timing = 6

    # ---------------- Penalties ----------------
    pen = 0
    if f.get("pitch_inbound") and not f.get("convs_two_way"):
        pen += 10
        reasons.append("vendor pitched you")
    if f.get("msgs_out_template") and not f.get("msgs_in"):
        pen += 3
    if f.get("group_only") and "messages" in f.get("sources", []):
        pen += 4
    total = max(0, min(100, rel + intent + fit + timing - pen))
    g = cfg["scoring"]
    grade = "A" if total >= g["grade_a"] else "B" if total >= g["grade_b"] else "C" if total >= g["grade_c"] else "D"

    track = _track(c, f, crm, prof, fit, fit_known, student, sen, fun, ver, cfg)
    if c.get("manual_track"):
        track = c["manual_track"]
    offer_key = _offer_key(track, fun, ver)
    topic = f.get("last_topic") or "your last conversation"
    offer_txt = cfg["offers"].get(offer_key, cfg["offers"]["default"])["en"]
    nxt = NEXT_ACTION[track].format(topic=topic, offer=offer_txt, vertical=ver or "relevant")
    return {
        "track": track, "score": total, "grade": grade, "s_rel": rel, "s_intent": intent, "s_fit": fit,
        "s_timing": timing, "fit_known": int(fit_known), "seniority": sen, "function": fun, "vertical": ver,
        "offer_key": offer_key, "next_action": nxt, "reasons": "; ".join(reasons[:6]), "student": student,
    }


ICP_FUNCS = ("hr", "marketing", "events", "innovation", "medical")


def _track(c, f, crm, prof, fit, fit_known, student, sen, fun, ver, cfg):
    fam = [s.lower() for s in cfg["sender"].get("family_surnames", [])]
    last = (c.get("name") or "").lower().split()
    if f.get("negative_last") or f.get("spam") or (last and last[-1] in fam):
        return "DNC"
    if c.get("stage") == "DNC":
        return "DNC"
    if student:
        return "STUDENT"
    tier = (crm.get("tier") or "").lower()
    if "past-buyer" in tier or "dormant" in tier:
        return "REACTIVATE"
    h = f.get("hits", {})
    two_way = f.get("convs_two_way") and not f.get("pitch_inbound")
    if two_way and h.get("price") and (h.get("xr") or h.get("meeting")):
        return "REACTIVATE"
    if "channel" in tier or (prof and AGENCY_RX.search(prof)):
        return "PARTNER"
    if two_way:
        return "WARM"  # never cold-pitch someone you've actually talked to
    if fit_known and fun != "recruiting":
        decision = sen in ("c_level", "director", "manager")
        if (fun in ICP_FUNCS and decision) or (ver and sen in ("c_level", "director")):
            return "ICP"
    if fit_known and FOUNDER_RX.search(prof):
        return "BUILDER"
    if fit_known:
        return "NETWORK"
    return "AUTO"


def _offer_key(track, fun, ver):
    if track == "STUDENT":
        return "student"
    if track == "PARTNER":
        return "agency"
    if track == "BUILDER":
        return "founder"
    if ver == "pharma" and fun in (None, "marketing", "medical", "sales"):
        return "pharma"
    if fun in ("hr", "marketing", "events", "innovation", "sales"):
        return fun
    return "default"
