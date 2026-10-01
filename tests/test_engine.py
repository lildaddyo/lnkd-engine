"""End-to-end test on a synthetic export (no real personal data). Run: python -m unittest discover tests"""
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from engine import classify, core, dashboard, segments, store  # noqa: E402

ME = "https://www.linkedin.com/in/me-test"


def _csv(header, rows):
    b = io.StringIO()
    w = csv.writer(b)
    w.writerow(header)
    w.writerows(rows)
    return b.getvalue()


def make_export(path):
    msgs = [
        # warm buyer: two-way, price + VR talk, 2 years ago
        ("c1", "", "Мария Иванова", "https://www.linkedin.com/in/maria-ivanova", "Me", ME, "2024-03-01 10:00:00 UTC",
         "", "Здравейте, интересува ни VR обучение, каква е цената?", "INBOX", ""),
        ("c1", "", "Me", ME, "Мария Иванова", "https://www.linkedin.com/in/maria-ivanova", "2024-03-01 11:00:00 UTC",
         "", "Ще ви изпратя оферта, може ли среща в четвъртък?", "INBOX", ""),
        # vendor pitch, never answered
        ("c2", "Grow your pipeline", "Spam Vendor", "https://www.linkedin.com/in/vendor-x", "Me", ME, "2025-01-01 10:00:00 UTC",
         "", "Hi! Our platform helps agencies with lead generation. " + "x" * 400 + " Book a call.", "INBOX", ""),
        # negative reply
        ("c3", "", "No Thanks", "https://www.linkedin.com/in/no-thanks", "Me", ME, "2025-05-01 10:00:00 UTC",
         "", "Not interested, please remove me.", "INBOX", ""),
        ("c3", "", "Me", ME, "No Thanks", "https://www.linkedin.com/in/no-thanks", "2025-04-30 10:00:00 UTC",
         "", "Hi there, quick question about VR", "INBOX", ""),
    ]
    mh = ["CONVERSATION ID", "CONVERSATION TITLE", "FROM", "SENDER PROFILE URL", "TO", "RECIPIENT PROFILE URLS",
          "DATE", "SUBJECT", "CONTENT", "FOLDER", "ATTACHMENTS"]
    inv = [("Me", "Pending Person", "9/28/26, 5:36 AM", "", "OUTGOING", ME, "https://www.linkedin.com/in/pending-person")]
    conns = "Notes:\n\"blah\"\n\n" + _csv(["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"], [
        ("Мария", "Иванова", "https://www.linkedin.com/in/maria-ivanova", "", "Zentiva", "Brand Manager", "01 Jan 2023"),
        ("Spam", "Vendor", "https://www.linkedin.com/in/vendor-x", "", "LeadCo", "Growth", "01 Jan 2025"),
        ("No", "Thanks", "https://www.linkedin.com/in/no-thanks", "", "Acme", "Engineer", "01 Jan 2025"),
        ("Hana", "Director", "https://www.linkedin.com/in/hana-hr", "", "UniCredit Bulbank", "Head of HR", "01 Mar 2024"),
        ("Peter", "Founder", "https://www.linkedin.com/in/peter-founder", "", "TinyStartup", "Founder & CEO", "01 Mar 2024"),
        ("Ana", "Agency", "https://www.linkedin.com/in/ana-agency", "", "Ogilvy", "Account Director", "01 Mar 2024"),
        ("Sam", "Student", "https://www.linkedin.com/in/sam-student", "", "Sofia University", "Student", "01 Mar 2024"),
        ("Tom", "Engineer", "https://www.linkedin.com/in/tom-eng", "", "SomeCo", "Software Engineer", "01 Mar 2024"),
        ("Ivan", "Raykov", "https://www.linkedin.com/in/family", "", "X", "Y", "01 Mar 2024"),
    ])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("messages.csv", _csv(mh, msgs))
        z.writestr("Invitations.csv", _csv(["From", "To", "Sent At", "Message", "Direction", "inviterProfileUrl", "inviteeProfileUrl"], inv))
        z.writestr("Connections.csv", conns)
        z.writestr("Endorsement_Received_Info.csv", _csv(
            ["Endorsement Date", "Skill Name", "Endorser First Name", "Endorser Last Name", "Endorser Public Url", "Endorsement Status"],
            [("2026/01/01 10:00:00 UTC", "VR", "Hana", "Director", "www.linkedin.com/in/hana-hr", "ACCEPTED")]))


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for d in ("data", "out", "inbox"):
            os.makedirs(os.path.join(self.tmp, d))
        shutil.copy(os.path.join(os.path.dirname(HERE), "config.json"), self.tmp)
        shutil.copy(os.path.join(os.path.dirname(HERE), "templates.json"), self.tmp)
        self._root = core.ROOT
        core.ROOT = self.tmp
        self.zip = os.path.join(self.tmp, "data", "export.zip")
        make_export(self.zip)
        self.cfg = core.load_cfg()
        self.db = core.open_db()
        core.do_import(self.db, self.cfg, self.zip)

    def tearDown(self):
        core.ROOT = self._root
        self.db.close()  # Windows cannot delete an open sqlite file
        shutil.rmtree(self.tmp)

    def track(self, slug):
        return self.db.execute("SELECT track FROM contacts WHERE key=?", ("linkedin.com/in/" + slug,)).fetchone()[0]

    def test_classification(self):
        self.assertEqual(self.track("maria-ivanova"), "REACTIVATE")
        self.assertEqual(self.track("no-thanks"), "DNC")
        self.assertEqual(self.track("family"), "DNC")
        self.assertEqual(self.track("hana-hr"), "ICP")
        self.assertEqual(self.track("peter-founder"), "BUILDER")
        self.assertEqual(self.track("ana-agency"), "PARTNER")
        self.assertEqual(self.track("sam-student"), "STUDENT")
        self.assertEqual(self.track("tom-eng"), "NETWORK")
        st = self.db.execute("SELECT stage FROM contacts WHERE key='linkedin.com/in/pending-person'").fetchone()[0]
        self.assertEqual(st, "NOT_CONNECTED")
        m = self.db.execute("SELECT score, lang FROM contacts WHERE key='linkedin.com/in/maria-ivanova'").fetchone()
        v = self.db.execute("SELECT score FROM contacts WHERE key='linkedin.com/in/vendor-x'").fetchone()
        self.assertGreater(m[0], v[0])
        self.assertEqual(m[1], "bg")

    def test_plan_sync_followup_reply(self):
        d = date(2026, 10, 5)  # Monday
        items, _ = core.plan(self.db, self.cfg, d, cap_override=20)
        keys = {i["profile_url"] for i in items}
        self.assertNotIn("https://www.linkedin.com/in/no-thanks", keys)
        self.assertNotIn("https://www.linkedin.com/in/family", keys)
        self.assertNotIn("https://www.linkedin.com/in/pending-person", keys)
        maria = next(i for i in items if "maria" in i["profile_url"])
        self.assertIn("Мария", maria["message"])
        self.assertIn("{hook}", maria["message"])
        # Cowork fills results
        res = os.path.join(self.tmp, "inbox", f"results_{d}.csv")
        with open(res, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            r["status"] = "sent"
            r["sent_at"] = f"{d}T10:00:00+00:00"
            r["final_message"] = "x"
        rows[-1]["status"] = "skipped_not_connected"
        with open(res, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=core.RESULT_COLS)
            w.writeheader()
            w.writerows(rows)
        rep = core.sync(self.db, self.cfg)
        self.assertEqual(rep["sent"], len(rows) - 1)
        # day +4: follow-ups due
        items2, _ = core.plan(self.db, self.cfg, date(2026, 10, 9), cap_override=20)
        self.assertTrue(any(i["touch"] == 2 for i in items2))
        # reply from Maria stops her sequence and moves stage
        with open(os.path.join(self.tmp, "inbox", "replies_2026-10-09.csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(core.REPLY_COLS)
            w.writerow(["https://www.linkedin.com/in/maria-ivanova", "2026-10-09T12:00:00+00:00", "positive", "meeting",
                        "wants demo", "Nova Person", "https://www.linkedin.com/in/nova-person"])
        rep = core.sync(self.db, self.cfg)
        self.assertEqual(rep["referrals"], 1)
        st = self.db.execute("SELECT stage FROM contacts WHERE key='linkedin.com/in/maria-ivanova'").fetchone()[0]
        self.assertEqual(st, "MEETING")
        nova = self.db.execute("SELECT features, s_rel FROM contacts WHERE key='linkedin.com/in/nova-person'").fetchone()
        self.assertIn("referred_by", json.loads(nova[0]))
        self.assertGreaterEqual(nova[1], 10)

    def test_dry_run_saves_nothing(self):
        d = date(2026, 10, 5)
        items, msg = core.plan(self.db, self.cfg, d, cap_override=5, dry_run=True)
        self.assertTrue(items)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM touches").fetchone()[0], 0)
        self.assertIsNone(store.meta_get(self.db, "start_date"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "inbox", f"results_{d}.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "out", f"dryrun_queue_{d}.csv")))

    def test_thompson_prefers_winner(self):
        import random
        stats = {("ICP", "en", "a"): [100, 2], ("ICP", "en", "b"): [100, 20]}
        rng = random.Random(1)
        picks = [core.choose_variant(self.cfg, stats, "ICP", "en", rng) for _ in range(200)]
        self.assertGreater(picks.count("b"), 180)

    def test_ramp(self):
        import random
        rng = random.Random(0)
        self.assertLessEqual(core.daily_cap(self.cfg, 1, rng), 44)
        caps = [core.daily_cap(self.cfg, 30, rng) for _ in range(50)]
        self.assertTrue(all(120 <= c <= 150 for c in caps))

    def test_templates_complete(self):
        t = self.cfg["templates"]
        for tr in ("REACTIVATE", "WARM", "ICP", "BUILDER", "PARTNER", "INVESTOR", "AIPEER", "STUDENT", "NETWORK"):
            for lang in ("bg", "en"):
                for n in ("1", "2", "3"):
                    self.assertIn("a", t[tr][lang][n], f"{tr}/{lang}/{n}")

    def test_segments(self):
        def seg(position, company="Acme", vertical=None, **kw):
            return segments.segment({"position": position, "company": company, "vertical": vertical,
                                     "features": kw.pop("features", {}), **kw})
        self.assertEqual(seg("Managing Partner", "Sofia Angels Ventures")["segment"], "INVESTOR")
        self.assertEqual(seg("HR Business Partner", "Galaxy Investment Group")["segment"], "INVESTOR_ORG_STAFF")
        self.assertEqual(seg("Founder & CEO", "Fusara AI")["segment"], "AI_BUILDER")
        self.assertEqual(seg("Head of Marketing", "DSK Bank", "banking")["segment"], "CORPORATE_BUYER")
        self.assertEqual(seg("Founder", "Alpha Digital Agency")["segment"], "PARTNER_AGENCY")
        self.assertEqual(seg("Chief Executive Officer", "Hyllbaz")["segment"], "SME_OWNER")
        self.assertEqual(seg("", "")["segment"], "UNKNOWN")
        self.assertEqual(seg("Student", "NBU")["segment"], "STUDENT_JUNIOR")
        crm = seg("Brand Manager", "Sopharma", features={"crm": {"tier": "tier:past-buyer"}})
        self.assertEqual((crm["segment"], crm["stream"]), ("CLIENT_PAST", "AICON"))
        hr = seg("Head of HR", "Postbank", "banking", s_rel=20, s_intent=8)
        self.assertEqual(hr["stream"], "VRX")
        self.assertIn(hr["opp_tier"], ("P1", "P2"))

    def test_segments_stored_and_exclusion_persists(self):
        row = self.db.execute("SELECT segment, opp_tier FROM contacts WHERE key='linkedin.com/in/hana-hr'").fetchone()
        self.assertIsNotNone(row["segment"])
        self.assertIsNotNone(row["opp_tier"])
        name = self.db.execute("SELECT name FROM contacts WHERE key='linkedin.com/in/hana-hr'").fetchone()[0]
        hit = core.exclude(self.db, name, "friend")
        self.assertEqual(hit, ["linkedin.com/in/hana-hr"])
        core.do_import(self.db, self.cfg, self.zip)  # a re-import must not resurrect them
        r = self.db.execute("SELECT stage, track FROM contacts WHERE key='linkedin.com/in/hana-hr'").fetchone()
        self.assertEqual((r["stage"], r["track"]), ("DNC", "DNC"))
        items, _ = core.plan(self.db, self.cfg, date(2026, 10, 7), cap_override=50, dry_run=True)
        self.assertFalse([i for i in items if "hana-hr" in i["profile_url"]])

    def _retitle(self, slug, position, company):
        key = "linkedin.com/in/" + slug
        self.db.execute("UPDATE contacts SET position=?, company=? WHERE key=?", (position, company, key))
        core.rescore(self.db, self.cfg, [key])
        return self.db.execute("SELECT track, segment, next_action FROM contacts WHERE key=?", (key,)).fetchone()

    def test_segment_tracks(self):
        r = self._retitle("tom-eng", "Managing Partner", "Sofia Angels Ventures")
        self.assertEqual((r["segment"], r["track"]), ("INVESTOR", "INVESTOR"))
        self.assertIn("Investor track", r["next_action"])
        r = self._retitle("peter-founder", "Founder & CEO", "Fusara AI")
        self.assertEqual((r["segment"], r["track"]), ("AI_BUILDER", "AIPEER"))
        # warm / reactivation / DNC tracks are never overridden by a segment track
        self.assertEqual(self._retitle("maria-ivanova", "Managing Partner", "Sofia Angels Ventures")["track"], "REACTIVATE")
        self.assertEqual(self._retitle("no-thanks", "Managing Partner", "Sofia Angels Ventures")["track"], "DNC")
        # and both new tracks render real messages
        c = core._contact(self.db.execute("SELECT * FROM contacts WHERE key='linkedin.com/in/tom-eng'").fetchone())
        for tr in ("INVESTOR", "AIPEER"):
            for lang in ("bg", "en"):
                for touch in (1, 2, 3):
                    self.assertTrue(core.render(self.cfg, c, tr, touch, "a", lang), f"{tr}/{lang}/{touch}")

    def test_crm_name_only_match_needs_company(self):
        from engine import ingest
        self.assertTrue(ingest._same_company("Postbank (Eurobank Bulgaria AD)", "Postbank"))
        self.assertFalse(ingest._same_company("Wolt", "Novartis"))
        self.assertFalse(ingest._same_company("", "Novartis"))
        name = self.db.execute("SELECT name FROM contacts WHERE key='linkedin.com/in/tom-eng'").fetchone()[0]
        co = self.db.execute("SELECT company FROM contacts WHERE key='linkedin.com/in/tom-eng'").fetchone()[0] or "Acme"
        crm = os.path.join(self.tmp, "data", "crm.csv")
        for company, expect_crm in (("Totally Different Corp", False), (co, True)):
            with open(crm, "w", encoding="utf-8", newline="") as fh:
                fh.write("name,company,role,tier,vertical,linkedin_url\n")
                fh.write(f'"{name}","{company}",Boss,tier:past-buyer,pharma,\n')
            core.do_import(self.db, self.cfg, self.zip, None, crm)
            f = json.loads(self.db.execute("SELECT features FROM contacts WHERE key='linkedin.com/in/tom-eng'").fetchone()[0])
            self.assertEqual(bool(f.get("crm")), expect_crm, company)
            self.assertEqual(bool(f.get("crm_candidates")), not expect_crm, company)

    def test_dashboard_builds_with_empty_campaign(self):
        html = dashboard.build(self.db)
        self.assertTrue(os.path.exists(html))
        data = dashboard.analytics(self.db)
        self.assertTrue(data["campaign"]["empty"])
        self.assertGreater(data["total"], 0)
        d, n = dashboard.export_csv(self.db)
        self.assertTrue(os.path.exists(os.path.join(d, "all_contacts_scored.csv")))


if __name__ == "__main__":
    unittest.main()
