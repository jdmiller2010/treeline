# Treeline development plan

Treeline is a house-to-house phone network for neighborhood kids. Every household is a **treehouse** with one phone line and one **4-digit number**. A kid lifts a real rotary phone (or a rotary softphone on a tablet), hears a dial tone, dials four digits, and the other treehouse's phone rings. It only connects when both families' parents have approved a **string** between their treehouses. It sounds and behaves like a 1960s phone, and it can't call 911 or any outside number.

This plan turns the decisions on the Treeline planning whiteboard into phases. Each phase ends with something that works end to end and can be tested.

- **Where we are:** Phases 1, 2 and 3 are built and tested (see the README's status table). Phase 4's deployment files, backups, alerts and privacy are built but haven't run on a public server, and the pilot hasn't happened. Phase 5 has a server side and a guide but hasn't been tried on an adapter. Phase 6 has server-side pairing and a design, with no firmware or board.
- **Where the plan and the build differ:** the nav's second tab is "Strings" (the design system had "Friends"); the printed pairing code on the Treeline phone is 10+ digits, not 6 (a code that lives for years must not be guessable); tablets pair by a short-lived six-digit code or QR. Everything else follows the phases below.

---

## Words we use

| Word | Meaning |
| --- | --- |
| **Treehouse** | A household: its grown-ups, kids and one phone line. |
| **Treeline number** | The 4 digits that ring a treehouse's line. One per treehouse, not per kid. |
| **Handset** | Anything that rings for a treehouse's line: a real rotary phone, or a softphone. A line can have several. |
| **String** | An approved connection between two treehouses. Both sets of parents say yes; after that, the kids call freely. |
| **Ladder code** | A one-time invite one parent shares with another family to start a string. |
| **Quiet hours / Pause** | Times a treehouse's line won't ring or call out, set by its own parents. |
| **The Treeline** | Everyone on the network. |

## Decisions already made

- One line and one 4-digit number per treehouse. No speed dials: you dial the number.
- A number only rings through if both treehouses' parents approved the string. Once approved, no further approval is needed. Quiet hours and pause still apply, on both sides.
- No outside calls in or out, and **no 911** for now. Every handset and the parent app say so plainly.
- Like an old phone: no caller ID, no announcing who's calling.
- Classic North American phone sounds (see [Sounds](#sounds)).
- Several handsets can share a line, like house extensions: all ring, any can answer, and picking one up mid-call joins the call with full talk. Everyone hears a click and a soft tone when a handset joins.
- Full call audit of every attempt; audio is never recorded.
- Code license: PolyForm Noncommercial 1.0.0; design assets: CC BY-NC 4.0; copyright Jordan Miller. Support link: Buy Me a Coffee.

---

## Phase 1: Platform core

**Goal:** the server knows treehouses, numbers, strings and handsets, and every call follows the new rules with the classic sounds and a full audit. Still tested with scripted phones and softphones on your PC.

**Build**

1. **Data model** (SQLite in the control app to start; it's one file and plenty for a pilot):
   - `treehouse`: id, name, number (4 digits), time zone, quiet hours, paused, call-length limit, daily-minutes limit, created, left.
   - `handset`: id, treehouse, kind (`rotary`, `ata`, `softphone`), name, SIP username and secret, last seen, removed.
   - `string`: treehouse A, treehouse B, state (`waiting`, `live`, `paused`, `cut`), who asked, who approved on each side, when.
   - `ladder_code`: code, from treehouse, expires, used.
   - `grown_up`: id, email, treehouse, role (`parent`, `sitter`).
   - `call`: see [Call audit](#call-audit).
   - `parent_action`: who, what, target, before and after, when.
2. **Numbers:** one per treehouse, assigned at random from 1000–9999 (0xxx is kept for the system, for example tests and recordings). A number is free to claim again as soon as a treehouse lets it go (a call only connects over a string both families approved, so a stale number can't reach anyone). Parents can change it.
3. **Dialing:** replace speed dials with 4-digit dialing in the dialplan. 911 goes to the 911 message; any other dial that isn't four digits "cannot be completed as dialed" (below).
4. **Call flow in the control app**, checked in this order:
   1. Is the caller's own line in quiet hours or paused? Then fast busy (from Phase 3 on, the handset plays it on pickup).
   2. Does the number exist? If not: three rising tones, "Your call cannot be completed as dialed. Please check the number and try again." (A dial that isn't four digits, and isn't 911, gets the same message.)
   3. Is there a live string between the two treehouses? If not: three tones, "You can't call that number from this phone. Ask a grown-up." The caller's parents get a note.
   4. Is the other line in quiet hours or paused? Then three tones and "The treehouse you're calling isn't taking calls right now. Please try again later." The same message for both, so a family's schedule isn't revealed.
   5. Is the other line already in use? Then busy signal.
   6. Is the other line offline (no handset registered)? Then fast busy.
   7. Otherwise: ring every handset on that line, play ringback to the caller, and connect the first to answer.
5. **Limits:** call length with three short pips a minute before the end; daily minutes; ring timeout (about a minute, then stop and log a missed call); repeat limits (for example no more than 5 calls to the same treehouse in 10 minutes); and a limit and flag on dialing numbers that aren't strung, to stop kids hunting through the 9,000 numbers.
6. **Safe defaults** for a new treehouse: quiet hours 8:00 pm to 7:00 am, 30-minute calls, pause one tap away.
7. **Time zones:** quiet hours follow each treehouse's own time zone and daylight saving.
8. **Sounds and recordings:** set Asterisk's indications to the US tones, add the SIT (three rising tones) and record the short operator-style messages (see [Sounds](#sounds)).
9. **Control API** for the parent app (a small REST service next to the control app): treehouses, strings, ladder codes, rules, handsets, calls and parent actions. Every change writes a `parent_action` row.
10. **Tests:** extend the scripted scenarios: dial by number, unknown number, not strung, quiet on either side, paused, busy, offline, ring timeout, time limit, repeat limit, 911.

**Done when:** all the scenarios pass, a softphone on your cell phone can dial another by 4-digit number, and every attempt shows up in the call audit with the right result.

---

## Phase 2: Parent app

**Goal:** parents run everything from a web app built with the design system: setting up, stringing treehouses, rules, and the call log. No more editing files.

**Build** (from `design/ui`, following `design/CLAUDE.md`; a web app that can be added to the home screen):

1. **Sign in** with an email code. Several grown-ups per treehouse; sitters get limited rights (can pause, can't approve or cut strings).
2. **Setup** (Steps): make your treehouse and get its number → read and accept "Treeline can't call 911" (a required checkbox) → pair the first handset → send a ladder code to a friend's family.
3. **Home** (Overview): the breeze or night card, alerts (strings waiting, a handset offline), this week's calls and minutes, and the no-911 reminder.
4. **Strings** (List and detail; the "Friends" tab becomes "Strings"): every strung treehouse and its number; approve, pause or cut; strings waiting on the other family; send a ladder code.
5. **Calls** (List and detail): the call audit with Today · This week · All, blocked attempts and why, missed calls, and a CSV export.
6. **Quiet hours and rules** (Settings form): quiet hours, call length, daily minutes, and pause now.
7. **Our treehouse:** the number, who lives here, handsets (rename, ring test, remove instantly), grown-ups and sitters.
8. **Phone book:** a printable card of every strung treehouse and its number, to keep by the phone.
9. **Account** (Menu): settings, privacy and safety, the parent action log, sign out, leave the Treeline (strings end, the other families are told, the number goes back to be claimed again), and delete the treehouse and all its data.
10. **Alerts:** email first (strings waiting, a handset offline, repeated blocked attempts, an optional evening summary); push notifications in Phase 4.
11. **Footer and about:** "© 2026 Jordan Miller · jdmiller2010@gmail.com · Support Treeline · Open-source licenses" at the bottom of every page. The licenses page is built from `THIRD_PARTY_NOTICES.md`.

**Done when:** two test families can set up from nothing, string their treehouses with a ladder code, change rules, and see the same call in both their logs, all without touching the server.

---

## Phase 3: Rotary softphone and shared lines

**Goal:** a kid can use a 1960s rotary phone on a tablet, and a treehouse can have several handsets on one line.

**Build**

1. **The softphone:** a web app built as an ordinary design-system page around the `RotaryPhone` (a 1960s desk rotary in Treeline's ink-and-watercolor hand, with a finger wheel that turns and a handset that lifts) sitting on a side table in a 90s room. The room's objects do the rest of the screen's job: a NO 911 sticker on the drawer, a card file holding the approved strings, a kid's drawing of the treehouse with its name, a quiet-time sticky note, a guide book on the shelf, a warranty card for the open-source licenses, a gift certificate for Buy Me a Coffee and a business card with the credit and contact. Drag a finger round the dial; lift the handset to answer, hang it up to end; each dial pulse can play a click. It plays the same sounds as the real phones and says "No 911. No outside calls." on the sticker on the drawer.
2. **Calls in the browser:** WebRTC to Asterisk over secure WebSockets (PJSIP's WebSocket transport) with a small SIP library in the page.
3. **Sign in with a QR code:** the softphone shows a QR code; a parent scans it in the parent app and approves; the tablet becomes a handset of that treehouse. Parents can remove it at any time and it stops working at once (lost or stolen tablets).
4. **Kid-proof:** nothing to set up or sign out of, no other screens. It only rings while open, so the docs recommend a dedicated tablet with the screen kept on and the tablet's kid lock (Guided Access or screen pinning).
5. **Shared lines:** each treehouse's line becomes a ring group plus a shared call bridge in the control app:
   - All handsets ring together; the first to answer joins the bridge.
   - While any handset is on the line, callers get a busy signal.
   - Picking up another handset mid-call joins the bridge with full talk, and everyone hears a click and a soft tone.
   - The softphone knows the line's state, so on pickup it plays dial tone, joins the call in progress, or plays fast busy during its own quiet hours.
6. **Audit:** which handsets rang, which answered, and who joined or left, with times.

**Done when:** a softphone and a SIP softphone in the same treehouse both ring, either answers, the other can join mid-call with the join tone, and outside callers get busy until both hang up.

---

## Phase 4: Deploy and pilot

**Goal:** Treeline runs on a small cloud server and 2–3 friend families use it every day, on softphones. No phone hardware needed yet.

**Build**

1. **Hosting:** the parent app and softphone on free static hosting (Firebase Hosting or GitHub Pages); Asterisk, the control app and the API on a small VM (Oracle Cloud Always Free, or about $5 a month on Lightsail, Hetzner or DigitalOcean).
2. **Security:** TLS for SIP and HTTPS everywhere, SRTP for audio, a unique password for every handset, ARI never exposed to the internet, rate limits on sign-in and SIP.
3. **Reliability:** nightly database backups, an uptime check, and an alert to parents when their handset goes offline. If the server is down, handsets fail with fast busy.
4. **Push notifications** for the parent app.
5. **Records:** call records kept 90 days by default, adjustable per treehouse; parent actions kept a year.
6. **Privacy before inviting anyone:** parent consent at setup, a short plain-language privacy policy (what's stored, for how long, who sees it, nothing recorded), and real deletion. The US kids' privacy law (COPPA) may apply once families beyond friends join; get advice before then.
7. **Pilot:** 2–3 families from the neighborhood, each with a dedicated tablet running the rotary softphone. Collect what confuses kids and parents and fix it before adding real phones in Phase 5.

**Done when:** the pilot families have used it for two weeks with no lost calls, no surprises in the audit, and every parent able to manage their treehouse alone.

---

## Phase 5: A real rotary phone through a SIP adapter

**Goal:** pilot families can add a real vintage rotary phone with an off-the-shelf adapter, alongside their softphones, before the custom build.

**Build**

1. **Grandstream HT801** (or similar ATA) with a Western Electric 500 or 2500, registered as a handset of its treehouse.
2. **Adapter settings:** pulse (rotary) dialing on, a 4-digit dial plan so it sends the call as soon as four digits are dialed, and US tones. Check pulse dialing on the exact model and firmware before buying more.
3. **Provisioning:** the parent app makes the adapter's settings file, so a parent only plugs it in and connects it to the router.
4. **A real extension for free:** other phones wired in parallel to the same adapter port act as true extensions, so the house already gets the "anyone can pick up" behavior with no extra work.
5. **Known limit:** the adapter makes its own dial tone, so fast busy during your own quiet hours comes after dialing, not on pickup. Phase 6 fixes this on the custom phone.
6. **Echo and volume:** tune the adapter's gain and echo settings for old carbon-style handsets.

**Done when:** a pilot family's rotary phone and softphone share their line, the rotary dials other treehouses by number, hears the right sound in every case in the call flow, and shows up in the audit as its own handset.

---

## Phase 6: Custom rotary phone

**Goal:** an unmodified vintage phone with Treeline built in: plug in power, join Wi-Fi, and it just works.

**Build**

1. **Hardware:** ESP32-S3 (with PSRAM) + ES8388 codec + AG1171 SLIC inside or under the phone, which rings the real bell and reads the real dial. The phone itself stays unmodified.
2. **Firmware:** a SIP client on ESP-ADF; rotary pulse counting; the classic tones generated on the phone; line state from the server so the phone plays dial tone, joins a call in progress, or plays fast busy on pickup during quiet hours.
3. **Wi-Fi setup:** from the parent app over Bluetooth or a setup hotspot, so other parents can do it without help.
4. **Security and updates:** per-device credentials, TLS and SRTP, and signed updates from the server.
5. **Audio:** echo cancellation and gain tuned for the original handset.
6. **Pairing:** a 6-digit code printed under the phone, entered in the parent app.

**Done when:** a pilot family swaps their adapter for the custom phone and nothing else changes for them.

---

## Sounds

Classic North American tones, so it feels like an old phone. Recordings are short and in an old-style operator voice.

| Sound | When | Tone |
| --- | --- | --- |
| Dial tone | Lift the handset | 350 + 440 Hz, steady |
| Ringback | The caller hears this while it rings | 440 + 480 Hz, 2 s on, 4 s off |
| The bell | The called phone rings | Same 2-on, 4-off rhythm |
| Busy signal | The other line is in use | 480 + 620 Hz, 0.5 s on, 0.5 s off |
| Fast busy | Pickup during your own quiet hours or pause; the other line is offline; the server is down | 480 + 620 Hz, 0.25 s on, 0.25 s off |
| Three rising tones (SIT) | Before every recording | 913.8, 1370.6, 1776.7 Hz |
| "Cannot be completed as dialed" | Unknown number, or not four digits | SIT, then recording |
| "Ask a grown-up" | Number isn't strung | SIT, then recording |
| "Isn't taking calls right now" | Other line in quiet hours or paused | SIT, then recording |
| "Use a grown-up's phone" | 911 | SIT, then "This phone can't call 911. Use a grown-up's phone." |
| Pips | A minute before the call-length limit | Three short beeps |
| Join tone | Another handset picks up mid-call | A click and a soft tone, heard by everyone |
| Hang-up | The other side hangs up | A click, a moment of quiet, then dial tone |
| Off-hook howler | Handset left off for 30 s without dialing | The loud howler, then silence |

## Call audit

One record for every attempt, allowed or not, shown in both treehouses' logs:

- Calling treehouse and handset; number dialed; called treehouse.
- Ring start, answer and end times; talk time.
- Result: connected, busy, no answer, not in service, not strung, quiet or paused, offline, 911 or wrong length, cut at the time limit, repeat limit.
- Which handsets rang, answered, joined and left, with times; who hung up first.
- Never any audio.

Parent actions (approve, pause or cut a string; change quiet hours or limits; add or remove a handset or grown-up) go in their own log with who did it and when.

## Safety and no 911

Treeline is not an emergency phone. It can't call 911 or any outside number, and that's said:

- on every phone's label and in the softphone's main screen,
- in parent setup, where a parent must tick "I understand",
- on the parent app's Home and About pages,
- in `README.md`.

## Later, not now

- Numbers for grown-ups, so a kid can ring a parent's app.
- Party line (three treehouses on one call), kid voicemail.
- More than one line per treehouse.
- Adding outside numbers or 911 through a real phone carrier (a large change with legal requirements).

## Still to decide

- What exactly the operator-voice recordings say, and who records them.
- Whether a treehouse can leave a string's other side a note when asking.
- Data retention defaults after the pilot.
