# Pilot: two or three families, two weeks

Phase 4 of [PLAN.md](PLAN.md) ends with a pilot: 2–3 friend families use Treeline every day on tablet phones, and nothing is added until the pilot goes well. This is the checklist. **The pilot itself can't be run for you.** It needs real families and a deployed server.

## Before you start

- [ ] Deployed per [DEPLOY.md](DEPLOY.md), `https://YOUR-DOMAIN/api/health` is green, and an uptime monitor is watching it.
- [ ] A restore from a backup has been tried at least once.
- [ ] The operator-voice messages are recorded (see `asterisk/sounds/README.md`), or you've decided to keep the placeholder voice for the pilot.
- [ ] Each family has a dedicated tablet, plugged in, locked to the Treeline phone (Guided Access or screen pinning).
- [ ] You've read the privacy page in the app. Every parent ticked the privacy box in setup. You've told the families what's stored and that nothing is recorded.
- [ ] You've asked a lawyer about children's privacy rules (COPPA) if any family isn't a personal friend.

## Telling the families

Say plainly, to the parents and to the kids:

- **It can't call 911 or any outside number.** The kids need another way to reach help, and should know it.
- Only treehouses both families approved can ring. Parents control who, when, and for how long.
- Nothing is recorded. Parents can see who called whom, when, and how it ended.
- The phone sleeps during quiet hours, on purpose.

## Each family, on day one

1. A parent signs in, makes the treehouse, and ticks both boxes.
2. A parent adds the tablet by QR code. Lift the handset, listen for the dial tone, ring another family.
3. Make a ladder code, send it, and approve the other family's request.
4. Set quiet hours and call limits together with the kids, so the rules aren't a surprise.
5. Show how to pause the line (one tap on Home) and where the call log is.

## What to watch, and write down

Keep a simple log for the two weeks: date, what happened, who was confused, what you changed.

- Do kids understand the dial and the tones without help? Where do they get stuck?
- Does the tablet ring every time, even after it has been asleep or restarted? Any missed calls the parents didn't expect?
- Does anything in the call log surprise a parent? Compare it with what really happened.
- Does a parent get stuck in the app? Where?
- Calls that dropped, echo, one-way audio, a tablet that went offline.

## Done when (from the plan)

- Two weeks in use, **no lost calls**, **no surprises in the audit**.
- **Every parent** can manage their treehouse alone: approve or cut a string, change quiet hours, pause, add or remove a phone.
- A list of what confused kids and parents, fixed or written down, before real phones are added in [ADAPTER.md](ADAPTER.md).
