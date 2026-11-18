# Operator messages

These short recordings play after the three rising tones when a call can't
connect. Asterisk plays them from `sounds/en/treeline/<name>.wav`.

The text of each message is in `messages.txt` (`name|words`). The Docker build
makes a plain placeholder voice from that text with eSpeak NG. To use a real
recording, drop an 8 kHz, 16-bit, mono WAV named `<name>.wav` in this folder
and rebuild (`docker compose up -d --build asterisk`). Files here win over the
placeholder voice.

Say the words in `messages.txt` exactly, in a calm, old-style operator voice.
Who records them is still to be decided (see docs/PLAN.md).
