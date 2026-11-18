# A real rotary phone through a phone adapter

Phase 5 of [PLAN.md](PLAN.md): a vintage phone with a Grandstream HT801 (or a similar analog telephone adapter, "ATA") that registers to Treeline as one handset of a treehouse.

> **Not tested on hardware.** The server side is tested: the adapter is just another SIP handset, and the project's scripted phones prove that every rule applies to it. But the work was done without an adapter or a rotary phone to hand. The settings below describe what each one must achieve. **Exact menu names and numbers differ between firmware versions**, so check each against your adapter's own manual. The settings file the parent app makes only fills in the account and the dial plan (see the end).

## What you need

- A Grandstream HT801 (one phone port) or similar ATA. Check that it supports **pulse (rotary) dialing**: a rotary phone sends pulses, not tones. Verify this on the exact model and firmware before buying more than one.
- A vintage rotary phone, such as a Western Electric 500 or 2500. Phones with the original bell ringer can be hard for an adapter to ring: check the adapter's ring load against the phone's. If the bell is weak or silent, try a different phone first.
- A network cable to the router.

## Add it in the parent app

Our treehouse, Add a phone, **Phone adapter**. Give it a name ("Hall phone"). The app then shows a **settings link** and the account: server, user ID and password. The password is shown **once**.

## Set the adapter

Plug it into power and the router, find its address (the router's device list, or the adapter's own IVR: pick up the phone and dial `***` then `02`), and open it in a browser.

| What | Set it to | Why |
| --- | --- | --- |
| SIP server | your domain (`phone.example.com`) | |
| SIP user ID, authenticate ID | the user ID the app showed | A random name; not a number |
| Authenticate password | the password the app showed | Unique to this phone |
| SIP transport | TLS (port 5061) | Production only. In the home test stack use UDP (port 5060) |
| SRTP | Enabled and required | Production only: the audio must be encrypted |
| **Pulse dialing** | On | A rotary dial sends pulses |
| Tones and ring | North America (US) | Dial tone 350+440 Hz, ringback 440+480 Hz, busy 480+620 Hz |
| Dial plan | `{ [1-9]xxx \| 0001 \| 911 \| x+ }` | Sends the call the moment four digits are dialed, instead of waiting a long time. `911` is sent at once so the phone can say it can't call 911. `0001` joins a call in progress |
| Off-hook warning | On, about 30 seconds | The loud howler if the handset is left off |
| Registration failed | Play fast busy (reorder) | So callers on the phone hear it when the server is down |
| Gain and echo | Start with defaults | Old carbon handsets often need the gain turned down a little; adjust by ear |

## What to expect

- **The dial tone comes from the adapter**, not Treeline. During quiet hours or a pause you'll hear the normal dial tone, and the fast busy comes *after* you dial. (The custom phone of Phase 6 plays it the moment you lift the handset.)
- **A real extension, free.** A second phone wired in parallel to the same adapter port rings with it and is a true extension: pick up either one. Treeline sees one handset.
- **Joining.** The adapter doesn't know a call is in progress on your line, so lifting a parallel phone mid-call joins the call at the phone level, with no click and tone. Tablets and Treeline phones do get the join tone.
- Several handsets in one treehouse all ring together, and the first to answer takes the call.

## The settings file

Under Our treehouse, a phone adapter has a **settings link**: a private address that returns an XML settings file with the server, user ID, password, account name and the dial plan above. In the adapter's web page, under Maintenance, Upgrade and Provisioning, you can point *Config Server Path* at the link. These are the Grandstream settings numbers the file uses: `P47` (SIP server), `P35` (user ID), `P36` (authenticate ID), `P34` (password), `P3` (name), `P290` (dial plan). **These numbers are from memory of Grandstream's provisioning guide and haven't been checked against a real adapter.** If the adapter ignores the file, enter the values by hand from the table above.

Removing the phone in the parent app invalidates the link and the account at once.
