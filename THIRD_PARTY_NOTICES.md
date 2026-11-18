# Third-party notices

Treeline's own code is under the PolyForm Noncommercial License 1.0.0 (see `LICENSE`), and its design assets under CC BY-NC 4.0 (see `design/LICENSE-ASSETS.txt`). Treeline also uses the open-source software below. Each keeps its own license; nothing here changes those terms.

This file is the source for the **Open-source licenses** page in the parent app and the softphone. Keep it up to date when a dependency is added or removed.

## Shipped with Treeline

| Component | Used for | License | Copyright |
| --- | --- | --- | --- |
| [Fraunces](https://github.com/undercasetype/Fraunces) | Display typeface (`design/ui/fonts/`) | SIL Open Font License 1.1 (`design/ui/fonts/OFL-Fraunces.txt`) | 2020 The Fraunces Project Authors |
| [Figtree](https://github.com/erikdkennedy/figtree) | Interface typeface (`design/ui/fonts/`) | SIL Open Font License 1.1 (`design/ui/fonts/OFL-Figtree.txt`) | 2022 The Figtree Project Authors |

## Installed by the containers (not copied into this repo)

| Component | Used for | License |
| --- | --- | --- |
| [Asterisk](https://www.asterisk.org/) (Ubuntu package `asterisk`) | Call server. Runs as its own program; Treeline talks to it over its REST interface (ARI). | GPL-2.0 |
| Asterisk core sounds, English (Ubuntu package `asterisk-core-sounds-en`) | Built-in prompts during development | CC BY-SA 3.0 |
| [Flask](https://github.com/pallets/flask) | The API | BSD-3-Clause |
| [gunicorn](https://github.com/benoitc/gunicorn) | Runs the API | MIT |
| [websocket-client](https://github.com/websocket-client/websocket-client) | Control app connection to Asterisk events | Apache-2.0 |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng) (Ubuntu package `espeak-ng`) | Builds the placeholder operator voice at image build time; not shipped in the running app | GPL-3.0-or-later |
| [SoX](https://sox.sourceforge.net/) (Ubuntu package `sox`) | Converts the operator messages to 8 kHz WAV at image build time | GPL-2.0-or-later |
| [SQLite](https://www.sqlite.org/) (built into Python) | The database | Public domain |
| [baresip](https://github.com/baresip/baresip) (Ubuntu package `baresip-core`) | Scripted test phones only | BSD-3-Clause |
| Ubuntu 24.04 and the official Python 3.12 image | Container base images | Various open-source licenses, listed in each image |

If you publish built container images, the GPL-2.0 and CC BY-SA 3.0 terms above apply to those images: include the license texts and point to the source of the packages (the Ubuntu archive).

## Planned (add here when used)

- ESP-IDF and ESP-ADF (Espressif) for the custom rotary phone firmware.
- The WebRTC/SIP library chosen for the tablet softphone.
