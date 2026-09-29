# Cowork runbook: daily LinkedIn outreach

This file is the instruction set Cowork follows every send day. Paste the **Daily task prompt** below into a Cowork scheduled task (weekdays, ~09:30 Europe/Sofia), with this `sales-engine` folder attached and Claude in Chrome logged in to LinkedIn.

The engine decides **who** gets **which** message. Cowork does only what a careful assistant would do by hand: open the profile, add one true personal line, send, and write down what happened.

---

## Daily task prompt (copy into Cowork)

> You run my LinkedIn outreach from the `sales-engine` folder. Follow `sales-engine/COWORK.md` exactly.
> 1. In the folder, run `python -m engine daily` (Windows: `py -m engine daily`). It syncs yesterday's results and writes today's queue.
> 2. Work through `out/queue_<today>.json` in order, following "Per-message procedure" in COWORK.md. After each item, fill in its row in `inbox/results_<today>.csv` straight away, not in a batch at the end.
> 3. Then do "Reply sweep" and write `inbox/replies_<today>.csv`.
> 4. Run `python -m engine sync`, then `python -m engine report --html`, and send me a 5-line summary: sent, skipped, replies by sentiment, meetings, and anything that needs me.
> Stop immediately and tell me if LinkedIn shows any warning, CAPTCHA, verification, limit notice, or "unusual activity" message.

---

## Hard rules (never break)

1. **Only send what is in today's queue.** Never add people, and never exceed the queue length.
2. **Pace like a human.** Wait a random 40–120 seconds between sends. Split the day into 2–3 sessions, for example 09:30, 13:00 and 16:00. Never send in bursts.
3. **Stop on any friction.** A CAPTCHA, a security check, a "weekly limit" or "unusual activity" banner, or a restricted-account notice means you stop all sending. Write `status=error` and `note=STOP: <what you saw>` for the current row and leave the rest blank. Then tell Ilian.
4. **Never send a message that still contains `{`, `}`, "[", or placeholder text.**
5. **Never add links to touch 1.** Touches 2 and 3 may carry a link only if Ilian adds one to templates.json.
6. **Never invent facts.** The `{hook}` line must be verifiably true from the profile you are looking at. If unsure, delete `{hook}`.
7. **Never reply to someone's answer on your own.** Replies go to the reply sweep: draft only, and Ilian approves.
8. **Don't message someone mid-conversation.** If the thread already has an unanswered message *from them*, or you messaged them in the last 21 days, skip with `status=skipped_other`, `note=active thread`, and log their message in the reply sweep.

## Per-message procedure

For each item in `out/queue_<date>.json`:

1. **Open `profile_url`** in Chrome. If there is no "Message" button, or it shows "Pending" or asks for InMail, record `status=skipped_not_connected` and move on.
2. **Read the profile top**: headline, current position and company, location, and the latest post or activity if visible. Copy the headline, company, position and location into the result row. Do this even if you skip, because it feeds the scoreboard.
3. **Check the track still fits.** For `AUTO` items, choose the track with the rules below and use `options[<TRACK>]`. For other items, if the profile clearly contradicts the track (for example it says ICP but they are now a student, or it says STUDENT but they are now a Head of HR), switch to the right track's message from `templates.json` (same touch, variant `a`) and record `chosen_track`.
4. **Check the language.** `lang` is a guess. Bulgarian location or a Cyrillic profile means `bg`; otherwise `en`. If it's wrong, use the same track, touch and variant from `templates.json` in the other language, and record `lang`. When writing Bulgarian to someone with a Latin-script name, keep the name as they write it unless the Cyrillic spelling is obvious (Мария, Георги, Иван).
5. **Write `{hook}`** (touch 1 only). Replace it with ONE sentence of at most 20 words, ending with a space, based on something specific and true:
   - a recent role change or promotion ("Congrats on the move to Head of Brand at X.")
   - a recent post topic ("Your post on onboarding Gen Z stuck with me.")
   - their company's visible news or product
   - otherwise, delete `{hook}` entirely.
   No flattery adjectives ("impressive", "amazing"), no "I came across your profile", no emojis.
6. **Final read.** The message is natural, has no placeholders, and is the right length. Bulgarian messages use the formal "Вие" in ICP/REACTIVATE/PARTNER/BUILDER/NETWORK and the informal "ти" in WARM/STUDENT, as written.
7. **Send**, then fill in the row: `status=sent`, `sent_at` (ISO time), `chosen_track`, `lang`, and `final_message` (exactly what was sent).

### Track rules for AUTO (and for re-checks)

| Profile says | Track |
|---|---|
| Student, intern, trainee, graduate, junior, assistant | STUDENT |
| Works at an agency, studio or production company, or is a freelancer (creative, events, PR, media) | PARTNER |
| HR, L&D, employer brand, marketing, brand, communications, events or innovation, at manager level or above | ICP |
| C-level or director at a pharma, banking, FMCG, telco or retail company (any function) | ICP |
| Founder, owner or CEO of a small company or startup | BUILDER |
| Anything else (engineers, sales ICs, recruiters, investors, public sector...) | NETWORK |

### Result row columns (`inbox/results_<date>.csv`, prefilled with touch_id + profile_url)

`status` (sent | skipped_not_connected | skipped_reclassify | skipped_other | error), `sent_at`, `chosen_track`, `lang`, `final_message`, `headline`, `company`, `position`, `location`, `note`

## Reply sweep (every send day, after sending)

1. Open LinkedIn Messaging and filter by **Unread**. Also review threads with anyone messaged in the last 21 days: `python -m engine report --json` lists who is in sequence, and the queue files show the names.
2. For every new reply, add a row to `inbox/replies_<date>.csv`:

   `profile_url, replied_at, sentiment, next_step, summary, referred_name, referred_url`

   - `sentiment`: **positive** (interest, asks for info, a demo or a call), **neutral** (polite, a question, "maybe later"), **referral** (points to someone else, so fill in `referred_name`/`referred_url`), **negative** (not interested), **dnc** (asks to stop, or is annoyed), **ooo** (auto-reply or away).
   - `next_step`: `meeting` if a call or meeting was agreed, `proposal` if they asked for an offer, otherwise empty.
   - `summary`: at most 15 words.
3. For each **positive, neutral or referral** reply, draft a response into `out/reply_drafts_<date>.md`. It should be short, answer their question, and for positive replies move to a specific time: "Would Thursday 11:00 or Friday 15:00 work for 20 min?" (Gong Labs: once interest is shown, a specific-time ask more than doubles booked meetings.) **Do not send drafts.** Ilian approves them.
4. With the VRX CRM connector: for positive or referral replies, create or update the contact (`create_linkedin_contact`, then `log_interaction`) and tag it `source:linkedin-engine`.

## What the engine does with your rows

- `sent`: the contact enters or continues the sequence. The next touch is scheduled at +4 days, then +10 days, and the contact moves to nurture 14 days after touch 3.
- Profile fields captured on any row mean the contact is re-scored and re-classified that night.
- Any reply stops the sequence. `positive` moves the contact to CONVERSATION, `meeting` to MEETING, `negative` to LOST, and `dnc` means they are never contacted again.
- A referral is added as a new contact with a warm-intro boost, and comes up in the queue in the next few days.
