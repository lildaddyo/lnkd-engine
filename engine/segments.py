"""Opportunity segments: who is this person to the business, and which revenue stream should the first offer come from?

Orthogonal to `classify.py` tracks (which decide *how* to approach someone). Segments decide *what we sell*:

  VRX    VR Express: XR/AR/3D, VR training and onboarding, activations, games
  AICON  AI Consultancy: AI strategy, workshops, digital humans and agents for enterprise
  AIBLD  AI Builds: custom agents, automations, apps, products
  PARTN  Partnerships and portfolio: white-label, co-delivery, referrals, capital

Rules are keyword matches on position + company (the export has no headlines). They are a first pass:
check the Data quality tab of the dashboard for what stays unclassified.
"""
import re

STREAMS = {
    "VRX": "VR Express: XR/AR/3D, VR training and onboarding, activations, games",
    "AICON": "AI Consultancy: AI strategy, workshops, digital humans and agents for enterprise",
    "AIBLD": "AI Builds: custom agents, automations, apps, products",
    "PARTN": "Partnerships and portfolio: white-label, co-delivery, referrals, capital",
}

SEGMENT_LABELS = {
    "UNKNOWN": "Unknown profile (needs enrichment)", "CLIENT_PAST": "Past clients (CRM)", "CORPORATE_BUYER": "Corporate buyers", "PARTNER_AGENCY": "Agencies / partners",
    "INVESTOR": "Investors", "AI_BUILDER": "AI builders", "TECH_FOUNDER": "Tech founders", "SME_OWNER": "SME owners",
    "INVESTOR_ORG_STAFF": "Investor-org staff", "CORPORATE_INFLUENCER": "Corporate influencers",
    "EDU_PUBLIC": "Edu / public", "RECRUITER": "Recruiters", "TALENT_IC": "Talent / ICs",
    "STUDENT_JUNIOR": "Students / juniors", "OTHER": "Other (unclassified)",
}

VERT_LABEL = {"pharma": "Pharma/Health", "banking": "Banking/Insurance/Fintech", "fmcg": "FMCG", "telco": "Telco",
              "retail": "Retail/E-com", "auto": "Automotive", "corporate": "Big corporate/IT"}


def _rx(*pats):
    return re.compile("|".join(pats), re.I)


INVESTOR = _rx(r"\binvestor", r"\bangel\b", r"venture", r"\bvc\b", r"private equity", r"family office",
               r"(?<!human )\bcapital\b(?! markets)", r"asset management", r"investment (fund|manager|director|partner|officer)",
               r"\bfund\b", r"фонд", r"инвеститор", r"business angel", r"seed (fund|stage)", r"limited partner",
               r"accelerator", r"акселератор", r"\binvestment\b(?! bank)")
INVESTOR_NOT = _rx(r"investment bank", r"human capital", r"capital markets")
INVESTOR_ROLE = _rx(r"investor", r"investment (director|manager|officer|partner)", r"portfolio", r"managing partner", r"venture partner")
AI_KW = _rx(r"\bAI\b", r"artificial intelligence", r"machine learning", r"\bML\b", r"\bLLM", r"gen ?ai", r"generative",
            r"prompt", r"automation", r"data scien", r"\bNLP\b", r"computer vision", r"chatbot", r"\bagents?\b",
            r"изкуствен интелект", r"автоматизац", r"deep learning", r"\bRPA\b", r"no-?code", r"low-?code")
AI_POS = _rx(r"\bAI\b", r"automation", r"machine", r"data scien")
TECH_BUILD = _rx(r"software", r"developer", r"engineer", r"програмист", r"\bCTO\b", r"technolog", r"tech\b", r"startup",
                 r"стартъп", r"saas", r"\bapp\b", r"full.?stack", r"devops", r"data (engineer|analyst)", r"\bIT\b",
                 r"indie", r"builder", r"product (owner|manager)", r"unity", r"unreal", r"game dev", r"\bXR\b", r"\bVR\b|\bAR\b")
FOUNDER = _rx(r"founder", r"co-?founder", r"owner", r"собственик", r"основател", r"управител", r"\bCEO\b",
              r"chief executive", r"managing (director|partner)", r"изпълнителен директор", r"entrepreneur", r"предприемач",
              r"president")
AGENCY_CO = _rx(r"agency", r"агенция", r"\bstudio\b", r"студио", r"creative", r"production", r"продукция", r"продуцент",
                r"producer", r"communications group", r"media group", r"advertising", r"реклама", r"\bPR\b", r"public relations",
                r"consult", r"консулт", r"software house", r"outsourc", r"integrator", r"reseller",
                r"event (agency|management|company)", r"ogilvy", r"havas", r"publicis", r"mccann", r"saatchi", r"wunderman",
                r"\bBBDO\b", r"\bDDB\b", r"leo burnett", r"\bTBWA\b", r"dentsu", r"branding", r"design (studio|house|agency)")
AGENCY_POS = _rx(r"agency", r"агенция", r"\bstudio\b", r"студио", r"creative (director|lead|strategist)", r"producer", r"продуцент",
                 r"account (director|manager|executive)", r"consultant", r"консултант", r"copywriter", r"art director")
SUPPORT_FN = _rx(r"human resources", r"\bHR\b", r"communications", r"marketing", r"\bCOO\b", r"operations", r"legal", r"counsel",
                 r"financ", r"account(ant|ing)", r"assistant", r"administrat", r"office manager", r"compliance", r"talent", r"people")
FREELANCE = _rx(r"freelanc", r"фрийланс", r"self.?employed", r"\bindependent\b")
BUY_FUNC = {
    "marketing": _rx(r"marketing", r"маркетинг", r"\bbrand", r"бранд", r"communicat", r"комуникаци", r"\bPR\b", r"digital",
                     r"дигитал", r"\bCMO\b", r"content", r"social media", r"trade marketing", r"\bCRM\b", r"e-?commerce",
                     r"public relations", r"corporate affairs", r"\bgrowth\b", r"product (manager|owner|marketing)",
                     r"customer (experience|success)", r"\bpromo"),
    "hr_learning": _rx(r"\bHR\b", r"human resources", r"човешки ресурси", r"people", r"talent", r"culture", r"L&D", r"learning",
                       r"training", r"обучени", r"employer brand", r"onboarding", r"employee", r"\bCHRO\b", r"internal comm"),
    "events": _rx(r"event", r"събити", r"experiential", r"activation", r"sponsorship", r"trade show", r"exhibition", r"congress", r"conference"),
    "innovation_it": _rx(r"innovation", r"иновац", r"transformation", r"трансформац", r"\bCIO\b", r"\bCTO\b", r"\bCDO\b",
                         r"\bIT\b", r"R&D", r"emerging"),
    "sales_bd": _rx(r"\bsales", r"продажб", r"business development", r"бизнес развитие", r"key account", r"commercial",
                    r"партньорств|partnership"),
    "ops_gm": _rx(r"operations", r"\bCOO\b", r"chief (operating|executive)", r"general manager", r"managing (director|partner)", r"country manager",
                  r"изпълнителен директор", r"\bCEO\b"),
}
SENIOR = _rx(r"\bCEO\b", r"\bCMO\b", r"\bCOO\b", r"\bCTO\b", r"\bCHRO\b", r"\bCFO\b", r"chief", r"\bboard\b", r"founder", r"owner",
             r"собственик", r"управител", r"основател", r"president", r"managing", r"director", r"директор", r"\bhead\b",
             r"\bVP\b", r"vice president", r"ръководител", r"country manager", r"general manager", r"partner\b")
MID = _rx(r"manager", r"мениджър", r"\blead\b", r"началник", r"senior")
STUDENT = _rx(r"\bstudent", r"студент", r"\bintern\b", r"internship", r"стажант", r"trainee", r"\bjunior\b", r"младши",
              r"assistant\b", r"асистент", r"apprentice", r"aspiring", r"ученик", r"graduate")
RECRUIT = _rx(r"recruit", r"рекрут", r"head ?hunter", r"talent acquisition", r"sourcer", r"подбор на персонал", r"staffing")
EDU = _rx(r"universit", r"универс", r"\bschool\b", r"училищ", r"academy", r"академия", r"professor", r"lecturer", r"преподавател",
          r"college", r"институт", r"\bedu", r"bootcamp", r"training (center|centre)")
PUBLIC = _rx(r"municipal", r"община", r"ministry", r"министерство", r"government", r"agency for", r"foundation", r"фондация",
             r"association", r"асоциация", r"chamber", r"камара", r"ngo", r"\bEU\b", r"european commission")
CREATIVE_IC = _rx(r"designer", r"дизайнер", r"artist", r"художник", r"illustrat", r"animat", r"3d", r"copywriter",
                  r"photograph", r"videograph", r"motion", r"editor", r"graphic")
TECH_IC = _rx(r"developer", r"engineer", r"програмист", r"инженер", r"unity", r"unreal", r"qa\b", r"devops",
              r"data (engineer|scientist|analyst)")

SEG_WEIGHT = {"CLIENT_PAST": 40, "CORPORATE_BUYER": 26, "INVESTOR": 24, "PARTNER_AGENCY": 24, "AI_BUILDER": 22,
              "TECH_FOUNDER": 20, "SME_OWNER": 20, "CORPORATE_INFLUENCER": 12, "INVESTOR_ORG_STAFF": 10, "EDU_PUBLIC": 10,
              "RECRUITER": 8, "TALENT_IC": 6, "STUDENT_JUNIOR": 3, "OTHER": 2, "UNKNOWN": 5}

CORP_STREAM = {  # buying function -> (primary, secondary, first offer)
    "hr_learning": ("VRX", ["AICON"], "VR onboarding and training games (ref. Postbank), AI learning assistants"),
    "events": ("VRX", ["AICON"], "VR/AR activations for events and launches (ref. Coca-Cola HBC, JTI)"),
    "marketing": ("VRX", ["AICON", "AIBLD"], "AR/3D activations, 3D configurators, AI digital humans (ref. Haleon, Recordati)"),
    "innovation_it": ("AICON", ["AIBLD", "VRX"], "AI strategy workshop and an agent/digital-human pilot"),
    "sales_bd": ("AICON", ["VRX"], "AI sales/CRM automation; interactive 3D/AR product demos"),
    "ops_gm": ("AICON", ["VRX", "AIBLD"], "Executive AI briefing and a scoped pilot"),
}

STATIC = {  # segment -> (primary, secondary, first offer)
    "CLIENT_PAST": ("AICON", ["VRX", "AIBLD"], "Reactivate: show what is new (AI agents, digital humans) on top of the previous work"),
    "INVESTOR": ("PARTN", ["AIBLD"], "Portfolio intro: VR Express track record and AI builds; ask about deal flow, co-invest or startup intros"),
    "INVESTOR_ORG_STAFF": ("PARTN", [], "Warm door into the investor org: ask for an intro to the investment team"),
    "AI_BUILDER": ("PARTN", ["AIBLD", "AICON"], "Builder-to-builder: co-build or white-label delivery, swap leads, share agents and XR pipeline"),
    "TECH_FOUNDER": ("AIBLD", ["PARTN"], "AI/automation build for their product or ops; XR/3D demo layer"),
    "PARTNER_AGENCY": ("PARTN", ["VRX", "AIBLD"], "White-label XR/AI production for their clients (they own the client, we deliver)"),
    "SME_OWNER": ("AIBLD", ["AICON", "VRX"], "Quick-win AI automation or agent build; AI consultancy audit; 3D/AR showcase"),
    "STUDENT_JUNIOR": ("AIBLD", [], "BrainTube-style product trial and community (low revenue; feedback and referrals)"),
    "RECRUITER": ("PARTN", ["VRX"], "Referral partner; VR/3D employer-brand and assessment for their clients"),
    "EDU_PUBLIC": ("VRX", ["AICON"], "VR/AI training pilots, workshops, grant-funded projects"),
    "TALENT_IC": ("PARTN", [], "Subcontractor / talent bench (3D, Unity, design); not a buyer"),
    "CORPORATE_INFLUENCER": ("VRX", ["AICON"], "Warm path into the buyer in their company; ask who owns the budget"),
    "OTHER": (None, [], "Low signal: hold in nurture"),
    "UNKNOWN": (None, [], "No title or company in the export: Cowork reads the live profile and re-segments before any send"),
}


def _n(s):
    return re.sub(r"\s+", " ", s or "").strip()


def segment(c):
    """c: contact dict (features parsed). Returns segment, stream, offer, opportunity score/tier/value."""
    f = c.get("features") or {}
    pos, co = _n(c.get("position")), _n(c.get("company"))
    txt = f"{pos} | {co}"
    vert = c.get("vertical")
    senior, mid = bool(SENIOR.search(pos)), bool(MID.search(pos))
    sen = "senior" if senior else "mid" if mid else "junior/IC"
    func = [k for k, p in BUY_FUNC.items() if p.search(pos)]
    is_inv = bool(INVESTOR.search(txt)) and not INVESTOR_NOT.search(txt)
    is_ai, is_tech = bool(AI_KW.search(txt)), bool(TECH_BUILD.search(txt))
    is_founder = bool(FOUNDER.search(pos))
    is_agency = bool(AGENCY_CO.search(co)) or bool(AGENCY_POS.search(pos))
    is_free = bool(FREELANCE.search(txt))
    is_student = bool(STUDENT.search(pos)) and not senior
    is_edu, is_pub = bool(EDU.search(txt)), bool(PUBLIC.search(txt))
    tier_crm = ((f.get("crm") or {}).get("tier") or "").lower()

    if "past-buyer" in tier_crm or "dormant" in tier_crm:
        seg = "CLIENT_PAST"
    elif is_inv and SUPPORT_FN.search(pos) and not INVESTOR_ROLE.search(pos):
        seg = "INVESTOR_ORG_STAFF"
    elif is_inv and (senior or is_founder or "invest" in txt.lower() or "venture" in txt.lower()):
        seg = "INVESTOR"
    elif is_ai and (is_tech or is_founder or AI_POS.search(pos)):
        seg = "AI_BUILDER"
    elif is_tech and is_founder and not is_agency:
        seg = "TECH_FOUNDER"
    elif is_agency or is_free:
        seg = "PARTNER_AGENCY"
    elif is_student:
        seg = "STUDENT_JUNIOR"
    elif RECRUIT.search(txt):
        seg = "RECRUITER"
    elif is_edu and not senior:
        seg = "EDU_PUBLIC"
    elif func and (senior or mid) and co and func != ["ops_gm"]:
        seg = "CORPORATE_BUYER"
    elif func == ["ops_gm"] and senior and co:
        seg = "CORPORATE_BUYER" if vert else "SME_OWNER"
    elif is_founder and co:
        seg = "SME_OWNER"
    elif is_edu or is_pub:
        seg = "EDU_PUBLIC"
    elif CREATIVE_IC.search(pos) or TECH_IC.search(pos):
        seg = "TALENT_IC"
    elif func:
        seg = "CORPORATE_INFLUENCER"
    elif not pos and not co:
        seg = "UNKNOWN"
    else:
        seg = "OTHER"

    if seg == "CORPORATE_BUYER":
        s1, s2, offer = CORP_STREAM[func[0]]
        if vert == "pharma":
            offer = "AI medical rep / AR portal (ref. Recordati, Merck); " + offer
        elif vert == "banking":
            offer = "VR onboarding/training (ref. Postbank, UniCredit); " + offer
    else:
        s1, s2, offer = STATIC[seg]

    vert_w = 8 if (vert in ("pharma", "banking", "fmcg", "telco") and seg in ("CORPORATE_BUYER", "CLIENT_PAST")) else 4 if vert else 0
    rel = min(30, c.get("s_rel") or 0) + min(15, c.get("s_intent") or 0) * 0.8
    score = int(min(100, SEG_WEIGHT[seg] + {"senior": 14, "mid": 7, "junior/IC": 1}[sen] + vert_w + rel * 0.6 + min(8, c.get("s_timing") or 0)))
    tier = "P1" if score >= 62 else "P2" if score >= 45 else "P3" if score >= 30 else "P4"
    if seg in ("CORPORATE_BUYER", "CLIENT_PAST") and senior and (vert or re.search(r"group|international|global|bank", txt, re.I)):
        value = "High (enterprise)"
    elif seg in ("CORPORATE_BUYER", "CLIENT_PAST", "PARTNER_AGENCY", "INVESTOR") or (seg in ("SME_OWNER", "AI_BUILDER", "TECH_FOUNDER") and senior):
        value = "Medium"
    else:
        value = "Low"
    return {"segment": seg, "stream": s1 or "", "stream2": ",".join(s2), "offer": offer, "opp_score": score,
            "opp_tier": tier, "value": value, "functions": ",".join(func), "vertical_label": VERT_LABEL.get(vert, "")}
