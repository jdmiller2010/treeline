# Third-party notices

Treeline's own code is under the PolyForm Noncommercial License 1.0.0 (see `LICENSE`), and its design assets under CC BY-NC 4.0 (see `design/LICENSE-ASSETS.txt`). Treeline also uses the open-source software below. Each keeps its own license; nothing here changes those terms.

This file is the source for the **Open-source licenses** page in the parent app and the softphone. Keep it up to date when a dependency is added or removed.

## Shipped with Treeline

| Component | Used for | License | Copyright |
| --- | --- | --- | --- |
| [Fraunces](https://github.com/undercasetype/Fraunces) | Display typeface (`design/ui/fonts/`) | SIL Open Font License 1.1 (`design/ui/fonts/OFL-Fraunces.txt`) | 2020 The Fraunces Project Authors |
| [Figtree](https://github.com/erikdkennedy/figtree) | Interface typeface (`design/ui/fonts/`) | SIL Open Font License 1.1 (`design/ui/fonts/OFL-Figtree.txt`) | 2022 The Figtree Project Authors |
| [Caveat](https://github.com/googlefonts/caveat) | Handwriting in the softphone room (`design/ui/fonts/`) | SIL Open Font License 1.1 (`design/ui/fonts/OFL-Caveat.txt`) | 2014 The Caveat Project Authors |
| [JsSIP](https://github.com/versatica/JsSIP) 3.11.1 | SIP over WebSocket in the softphone (`web/phone/vendor/jssip.min.js`, a minified build from cdnjs) | MIT (`web/phone/vendor/LICENSE-JsSIP.txt`) | 2012-2026 José Luis Millán and Iñaki Baz Castillo |
| [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 1.4.4 | The QR codes in the parent app and on the softphone's pairing screen (`design/ui/js/vendor/qrcode.js`) | MIT | 2009 Kazuhiko Arase |

"QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

## Installed by the containers (not copied into this repo)

| Component | Used for | License |
| --- | --- | --- |
| [Asterisk](https://www.asterisk.org/) (Ubuntu package `asterisk`) | Call server. Runs as its own program; Treeline talks to it over its REST interface (ARI). | GPL-2.0 |
| Asterisk core sounds, English (Ubuntu package `asterisk-core-sounds-en`) | Built-in prompts during development | CC BY-SA 3.0 |
| [Flask](https://github.com/pallets/flask) | The API | BSD-3-Clause |
| [gunicorn](https://github.com/benoitc/gunicorn) | Runs the API | MIT |
| [pywebpush](https://github.com/web-push-libs/pywebpush) 2.5.0 and [py-vapid](https://github.com/web-push-libs/vapid) 1.9.6 | Notifications on parents' phones and the key generator | MPL-2.0 (used unmodified, as installed from PyPI) |
| [http-ece](https://github.com/web-push-libs/encrypted-content-encoding) 1.2.1 | Encrypts those notifications | MIT |
| [cryptography](https://github.com/pyca/cryptography) | Used by the above | Apache-2.0 or BSD-3-Clause |
| [Caddy](https://caddyserver.com/) (Ubuntu package `caddy` 2.6.2 on the VM; the `caddy:2` image for local HTTPS) | HTTPS and certificates | Apache-2.0 |
| [boto3](https://github.com/boto/boto3), [botocore](https://github.com/boto/botocore), [s3transfer](https://github.com/boto/s3transfer), [jmespath](https://github.com/jmespath/jmespath.py), [python-dateutil](https://github.com/dateutil/dateutil), [six](https://github.com/benjaminp/six) and [urllib3](https://github.com/urllib3/urllib3) (pinned with hashes in `deploy/native/requirements-tools.lock`) | The VM's root-run tools: reading secrets from SSM, uploading backups to S3 | Apache-2.0 (boto3, botocore, s3transfer, python-dateutil), MIT (jmespath, urllib3), MIT (six) |
| [age](https://github.com/FiloSottile/age) (Ubuntu package `age`) | Encrypts backups before they leave the VM | BSD-3-Clause |
| [OpenSSH](https://www.openssh.com/) `ssh-keygen` (Ubuntu package `openssh-client`) | Signs releases (`-Y sign`) and verifies them on the VM (`-Y verify`) | BSD-style (OpenSSH) |
| [fail2ban](https://github.com/fail2ban/fail2ban) (Ubuntu package `fail2ban`) | Bans addresses that guess SIP accounts | GPL-2.0-or-later |
| [AWS CDK](https://github.com/aws/aws-cdk) (`aws-cdk` CLI and `aws-cdk-lib`, pinned in `infra/`) | Describes the AWS infrastructure as code; run from the owner's computer only, never on the VM and never at runtime | Apache-2.0 |
| [websocket-client](https://github.com/websocket-client/websocket-client) | Control app connection to Asterisk events | Apache-2.0 |
| [eSpeak NG](https://github.com/espeak-ng/espeak-ng) (Ubuntu package `espeak-ng`) | Builds the placeholder operator voice at image build time; not shipped in the running app | GPL-3.0-or-later |
| [SoX](https://sox.sourceforge.net/) (Ubuntu package `sox`) | Converts the operator messages to 8 kHz WAV at image build time | GPL-2.0-or-later |
| [SQLite](https://www.sqlite.org/) (built into Python) | The database | Public domain |
| [Playwright](https://github.com/microsoft/playwright) (Python package and the `mcr.microsoft.com/playwright/python` image) | Browser tests only; never part of a deployment | Apache-2.0 |
| [baresip](https://github.com/baresip/baresip) (Ubuntu package `baresip-core`) | Scripted test phones only | BSD-3-Clause |
| Ubuntu 24.04 and the official Python 3.12 image | Container base images | Various open-source licenses, listed in each image |

If you publish built container images, the GPL-2.0 and CC BY-SA 3.0 terms above apply to those images: include the license texts and point to the source of the packages (the Ubuntu archive).

## Planned (add here when used)

- ESP-IDF and ESP-ADF (Espressif) for the custom rotary phone firmware.
