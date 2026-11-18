# The Treeline rotary phone (Phase 6)

An unmodified vintage rotary phone with Treeline built in: plug in power, join Wi-Fi, and it works. This is Phase 6 of [PLAN.md](PLAN.md).

> **Status: design and server support only.** The firmware and the board are **not built**. There was no hardware to build or test them on, and writing untested firmware for a device that drives a ringer at high voltage would not be responsible. What exists and is tested: the server-side pairing for a factory-registered phone (below). Everything else here is a design to build against, with the open questions called out. Check every pin and voltage against the parts' datasheets.

## Parts

| Part | Role |
| --- | --- |
| ESP32-S3 with PSRAM | Wi-Fi, SIP over TLS, audio, and the state machine |
| ES8388 audio codec | Talks to the handset's microphone and earpiece |
| AG1171 SLIC (subscriber line interface) | Presents a phone line to the vintage phone: feeds it current, detects the hook switch and the dial pulses, and rings the bell |
| A ring-voltage supply | The bell needs about 70–90 V AC at 20 Hz. Most AG1171 modules include a boost; confirm yours does |
| A power supply for the board | USB or a small wall adapter |

The phone itself stays unmodified: its own cord plugs into the SLIC board.

## What the firmware does

```
 hook switch / dial pulses --SLIC--> ESP32-S3 <--I2S--> ES8388 <--analog--> handset
                                       |  Wi-Fi
                                       v
                                 SIP over TLS + SRTP  -->  Treeline
```

1. **Dial pulses.** A rotary dial opens and closes the line about ten times a second. The firmware counts breaks to read digits, with an inter-digit gap of about 300–700 ms between digits. Ignore the hook-switch "bounce" and the hook flash (a short on-hook tap).
2. **Tones, made on the phone.** Dial tone 350+440 Hz; ringback 440+480 Hz, 2 s on, 4 s off; busy 480+620 Hz, 0.5 s on and off; fast busy 480+620 Hz, 0.25 s on and off; the off-hook howler after 30 s. The same table the softphone uses (`web/phone/js/tones.js`).
3. **Line state from the server.** On pickup the phone asks `GET /api/line` (HTTP Basic with its own SIP account), exactly as the tablet does, and plays dial tone, joins a call in progress by dialing `0001`, or plays fast busy during quiet hours. Because the phone plays its own tones, *this* is where quiet hours finally give fast busy the instant the handset is lifted, which the adapter of Phase 5 can't do.
4. **Calls.** SIP over TLS (port 5061) with SRTP, registering as a handset of kind `rotary`. G.711 (µ-law or A-law) is enough.
5. **Ringing.** On an incoming call, drive the SLIC's ring mode at 20 Hz in a 2 s on, 4 s off cadence, and stop on hook-off.
6. **Updates.** Signed firmware images fetched over HTTPS from the server, verified before they're written.

## Pairing: a code under the phone

At the factory, or with a programming jig, each phone is given a random **pairing code** (printed on a label underneath) and a random **device secret** (kept only in the phone's flash). The jig registers the pair with the server:

```
POST /api/factory/devices
X-Factory-Key: <TREELINE_FACTORY_KEY>
{ "code": "1234567890", "token": "<at least 24 random characters>" }
```

The endpoint is off unless the server has `TREELINE_FACTORY_KEY` set. The first time the phone is on Wi-Fi it polls `GET /api/pair/status?token=<device secret>`. A parent opens Our treehouse, Add a phone, **Treeline rotary phone**, and types the code. The server then makes the handset and the phone's next poll returns its SIP account (once). Removing the phone in the parent app drops it at once.

**The printed code is at least 10 digits, not 6 as the plan first said.** A softphone's six digits only live for 10 minutes, but a code on a label lives for years, and with only a million six-digit codes another family could guess one and claim your phone. Claims are also rate-limited per parent and for everyone.

**Known gap:** a pairing is single use. If a phone is factory-reset after pairing it has to be re-registered at the jig. If that isn't acceptable, give each phone a way to ask the server to reissue its account to the same secret.

## Open questions

- **The SIP stack.** The biggest unknown is which SIP client runs on the ESP32-S3 with TLS and SRTP. ESP-ADF has a SIP example; whether it supports SRTP, and how well, needs checking. A fallback is a small custom client for the one call pattern Treeline uses.
- **Echo and gain** for the original carbon handset: acoustic echo cancellation in ESP-ADF, tuned by ear.
- **Ring voltage safety.** The bell supply is hazardous. Build it enclosed, fused, and follow the SLIC module's guidance.
- **Wi-Fi setup** by a parent: over Bluetooth from the parent app or a setup hotspot. Not designed here beyond that.
- **Certification** for selling hardware in the US (FCC, and the line-side rules for telephone equipment).
