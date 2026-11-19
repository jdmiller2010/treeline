// Installing Treeline: the small card on the first screen, the full install page for phones and tablets, and the menu item.
import { button, html, icon, raw, setBusy, str } from "/shared/ui.js";
import { canPromptInstall, device, isStandalone, justInstalled, onInstallChange, platform, promptInstall } from "/shared/pwa.js";

/** Can this device install the app from here? The browser's prompt (Android, desktop Chrome), or an iPhone or iPad's Share menu. */
export const installAvailable = () => !isStandalone() && !justInstalled() && (canPromptInstall() || platform() === "ios");

const OPEN = "Open <strong>Treeline</strong> from your Home Screen.";

/** The steps for this device and browser, as { who, items, note }: the buttons are named the way that browser names them. */
export function installRecipe(d = device()) {
  const { os, browser, inApp, tablet } = d;
  const kind = os === "ios" ? (tablet ? "iPad" : "iPhone") : os === "android" ? (tablet ? "Android tablet" : "Android phone") : "this device";
  if (inApp) {
    const target = os === "ios" ? "Safari" : "Chrome";
    return { who: `A browser inside another app on your ${kind}`, items: [`Open this page in <strong>${target}</strong>: use the app's menu and choose <strong>Open in browser</strong>, or copy the address into ${target}.`, "Then press Install Treeline again."] };
  }
  if (os === "ios") {
    const share = tablet ? "the <strong>Share</strong> button (a square with an arrow) at the top of the screen" : "the <strong>Share</strong> button (a square with an arrow) at the bottom of the screen";
    const note = "On an iPhone or iPad, Treeline has to be installed to ring for calls and send alerts.";
    if (browser === "safari") return { who: `Safari on your ${kind}`, items: [`Tap ${share}. If you don't see it, tap <strong>⋯</strong> first.`, "Scroll down and tap <strong>Add to Home Screen</strong>, then <strong>Add</strong>.", OPEN], note };
    if (browser === "firefox") return { who: `Firefox on your ${kind}`, items: ["Tap the <strong>menu</strong> (three lines), then <strong>Share</strong>.", "Tap <strong>Add to Home Screen</strong>, then <strong>Add</strong>.", OPEN], note };
    return { who: `${browser === "chrome" ? "Chrome" : browser === "edge" ? "Edge" : "Your browser"} on your ${kind}`, items: ["Tap the <strong>Share</strong> button next to the address, or the <strong>⋯</strong> menu then <strong>Share</strong>.", "Tap <strong>Add to Home Screen</strong>, then <strong>Add</strong>. (If you don't see it, open this page in Safari and use Share there.)", OPEN], note };
  }
  if (os === "android") {
    if (browser === "samsung") return { who: `Samsung Internet on your ${kind}`, items: ["Tap the <strong>menu</strong> (three lines).", "Tap <strong>Add page to</strong>, then <strong>Home screen</strong>.", OPEN] };
    if (browser === "firefox") return { who: `Firefox on your ${kind}`, items: ["Tap the <strong>menu</strong> (three dots).", "Tap <strong>Install</strong>.", OPEN] };
    if (browser === "edge") return { who: `Edge on your ${kind}`, items: ["Tap the <strong>menu</strong> (three lines at the bottom).", "Tap <strong>Add to phone</strong>.", OPEN] };
    if (browser === "opera") return { who: `Opera on your ${kind}`, items: ["Tap the <strong>menu</strong> (three dots).", "Tap <strong>Home screen</strong>.", OPEN] };
    return { who: `Chrome on your ${kind}`, items: ["Tap the <strong>menu</strong> (three dots, top right).", "Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>, then <strong>Install</strong>.", OPEN] };
  }
  return { who: "Your browser", items: ["Open the browser's menu.", "Choose <strong>Install</strong> or <strong>Add to Home screen</strong>.", OPEN] };
}

/** The steps for a device that has no install prompt of its own, worded for this device and browser. */
export function installSteps(d) {
  const r = installRecipe(d);
  return html`<p class="tl-card__body" style="margin:0"><strong>${r.who}</strong></p>
    <ol class="tl-card__body" style="margin:0;padding-left:1.25em">${r.items.map((i) => html`<li>${raw(i)}</li>`)}</ol>
    ${r.note ? html`<p class="tl-card__body">${r.note}</p>` : ""}`;
}

/** Install now where the browser allows it. Resolves "accepted", "dismissed", or "steps" when the person has to do it by hand.
 *  The browser decides when a page may offer the install, and tells us with an event that can come a moment after the page loads, so `wait` is how
 *  many milliseconds to give it before giving up. */
export async function runInstall(wait = 0) {
  if (!canPromptInstall() && wait) {
    await new Promise((done) => {
      const t = setTimeout(() => { off(); done(); }, wait);
      const off = onInstallChange(() => { if (canPromptInstall()) { clearTimeout(t); off(); done(); } });
    });
  }
  if (!canPromptInstall()) return "steps";
  return (await promptInstall()) ? "accepted" : "dismissed";
}

/** One plain sentence on why the browser isn't offering one-tap install, for the person looking at the steps. */
export async function whyNotOneTap() {
  if (device().inApp) return "This is a browser inside another app, and those can't install apps.";
  if (platform() === "ios") return "iPhones and iPads have no one-tap install: Apple only allows it through the Share menu.";
  if (!window.isSecureContext) return "This address isn't a secure (https) address, so the browser won't offer one-tap install.";
  let reg = null;
  try { reg = await navigator.serviceWorker?.getRegistration("/"); } catch { /* none */ }
  if (!reg) return "The browser hasn't finished setting Treeline up, or won't run it here (an https certificate it doesn't trust stops that). Reload the page and try again.";
  return "This browser hasn't offered one-tap install for Treeline. If you installed or dismissed it before, Chrome waits a while before offering it again.";
}

export function mountInstall(slot) {
  const draw = () => {
    if (!slot.isConnected) return;
    if (isStandalone()) { slot.innerHTML = ""; return; }
    if (canPromptInstall()) {
      slot.innerHTML = str(html`<section class="tl-card"><div class="tl-stack tl-stack--group">
        <div class="tl-stack tl-stack--tight"><h2 class="tl-card__title">Install Treeline</h2>
        <p class="tl-card__body">Put it on this device's Home Screen so it opens like an app, rings for calls and sends alerts.</p></div>
        <div class="tl-actions">${button({ label: "Install Treeline", variant: "secondary", attrs: "data-install" })}</div></div></section>`);
      slot.querySelector("[data-install]").addEventListener("click", () => promptInstall());
    } else if (platform() === "ios") {
      slot.innerHTML = str(html`<section class="tl-card"><div class="tl-stack tl-stack--tight">
        <h2 class="tl-card__title">Install Treeline</h2>
        <p class="tl-card__body">Tap the Share button, then Add to Home Screen. On an iPhone or iPad, Treeline has to be installed to ring and to send alerts.</p></div></section>`);
    } else slot.innerHTML = "";
  };
  draw();
  onInstallChange(draw);
}

/** The install page a phone or tablet in a browser tab sees first: one button that installs the app, and a quiet link to carry on in the browser.
 *  Where the browser lets a page start the install (Android, desktop Chrome) the button does it. Where it can't (an iPhone or iPad, or a browser
 *  that hasn't offered the prompt), the button shows the steps instead. */
export function mountInstallPage(slot, { onBrowser }) {
  let steps = false, why = "";
  const draw = () => {
    if (!slot.isConnected) return;
    const label = platform() === "ios" && !canPromptInstall() ? "Show me how to install" : "Install Treeline";
    const body = justInstalled()
      ? html`<div class="tl-alert tl-alert--success" role="status"><span class="tl-alert__icon" aria-hidden="true">${icon("check")}</span><div>
          <p class="tl-alert__title">Treeline is installed</p><p class="tl-alert__body">Open it from your Home Screen.</p></div></div>`
      : html`<div class="tl-actions">${button({ label, variant: "primary", size: "lg", attrs: { "data-install": "" } })}</div>
          ${steps && !canPromptInstall() ? html`<section class="tl-card" id="install-steps"><div class="tl-stack tl-stack--group"><h2 class="tl-card__title">Add Treeline to your Home Screen</h2>${why ? html`<p class="tl-card__body" id="install-why" style="color:var(--ink-muted)">${why}</p>` : ""}${installSteps()}</div></section>` : ""}`;
    slot.innerHTML = str(html`<div class="tl-stack tl-stack--group">${body}
      <p class="caption" style="margin:0"><a href="#" data-browser style="color:var(--ink-muted);text-decoration:underline">Use Treeline in your browser instead</a></p></div>`);
    slot.querySelector("[data-install]")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      setBusy(btn, true, "Checking");
      if (await runInstall(canPromptInstall() ? 0 : 2500) === "steps") {
        why = await whyNotOneTap(); steps = true; draw();
        slot.querySelector("#install-steps")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } else setBusy(btn, false);
    });
    slot.querySelector("[data-browser]").addEventListener("click", (e) => { e.preventDefault(); onBrowser(); });
  };
  draw();
  onInstallChange(draw);
}
