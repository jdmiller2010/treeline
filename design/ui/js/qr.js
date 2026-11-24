/* Treeline QR codes: TLQR.svg(text) draws a QR code as one inline SVG path, with no network and nothing to install.
 * Load it after vendor/qrcode.js (the encoder, "QR Code Generator for JavaScript" 1.4.4 by Kazuhiko Arase, MIT; "QR Code" is a
 * registered trademark of DENSO WAVE INCORPORATED).
 *
 *   TLQR.svg("https://…", { label: "QR code for …", level: "M" })  ->  '<svg class="tl-qr__svg" …>…</svg>'
 *
 * Square modules in the current text color; put it on the .tl-qr paper (components/QrCode) so a camera always gets the quiet
 * zone and the contrast it needs, in either theme. */
(function () {

window.TLQR = {
  /** An SVG string for `text`. Square modules, one path, crisp edges; the size is the container's. */
  svg(text, { label = "QR code", level = "M" } = {}) {
    const q = window.qrcode(0, level); q.addData(String(text), "Byte"); q.make();
    const n = q.getModuleCount(); let d = "";
    for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (q.isDark(r, c)) d += "M" + c + " " + r + "h1v1h-1z";
    const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
    return '<svg class="tl-qr__svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + n + " " + n + '" role="img" aria-label="' + esc(label) + '" shape-rendering="crispEdges"><path d="' + d + '" fill="currentColor"/></svg>';
  },
};
})();
