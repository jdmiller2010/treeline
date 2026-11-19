// "Install Treeline", on the screens a new device sees first. Installed, it has nothing to show.
import { button, html, str } from "/shared/ui.js";
import { canPromptInstall, isStandalone, onInstallChange, platform, promptInstall } from "/shared/pwa.js";

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
