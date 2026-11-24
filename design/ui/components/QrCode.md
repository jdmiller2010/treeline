# QrCode and CodeShow

A QR code on its own white paper, and a code read out big beside its Copy button. Together they are how a family hands someone a string: scan the QR code or type the code.

**Consumer provides:** the text to encode, an accessible label, and for `CodeShow` the code and its note. Build the code with `TLQR.svg(text, { label })` from `js/qr.js` (it needs `js/vendor/qrcode.js`, MIT, listed in THIRD_PARTY_NOTICES.md).

- `.tl-qr` is always dark on white, in both themes, with a 14px quiet zone: a camera needs the contrast, so it never follows dark mode. At most 224px wide; the code is one SVG path with crisp square modules, so it scales without blurring.
- The QR code is a shortcut, never the only way: always show the written code next to it (`.tl-codeshow`: 26px mono, wide tracking, tap to select all) and say what scanning does.
- Encode a full link (`https://…/parent/#/string/CODE`), so the phone's own camera app opens Treeline, not a code to type.
- Give the QR an `aria-label` that says what it is for ("QR code for the string code ABCD-2345"). The written code is the accessible route.

## HTML

See `components/QrCode.html` for the QR code and the code line.
