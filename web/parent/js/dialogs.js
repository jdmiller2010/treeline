// Focused tasks: a Sheet over the current screen (bottom sheet on phones, dialog on desktop).
import { ApiError } from "/shared/api.js";
import { alert, html, iconButton, nextId, str, button, setBusy } from "/shared/ui.js";

/**
 * Open a sheet with a form. `onSubmit(form)` runs when the primary button is
 * pressed; throw an ApiError (or any Error) to show its message inside the
 * sheet. Resolves with onSubmit's value, or null if the sheet was closed.
 */
export function formDialog({ title, intro, body, submit = "Save", cancel = "Cancel", danger = false, onSubmit, onOpen }) {
  return new Promise((resolve) => {
    const id = nextId("dlg");
    const scrim = document.createElement("div");
    scrim.className = "tl-sheet-scrim";
    scrim.id = id;
    scrim.hidden = true;
    scrim.innerHTML = str(html`<div class="tl-sheet" role="dialog" aria-modal="true" aria-labelledby="${id}-title">
  <span class="tl-sheet__grabber" aria-hidden="true"></span>
  <div class="tl-sheet__head"><h2 class="tl-sheet__title" id="${id}-title">${title}</h2>${iconButton({ label: "Close", name: "close", extra: "tl-sheet__close" })}</div>
  <form class="tl-stack tl-stack--group" novalidate>
    ${intro ? html`<p class="tl-sheet__body">${intro}</p>` : ""}
    ${body || ""}
    <div data-error></div>
    <div class="tl-actions">
      ${cancel ? button({ label: cancel, variant: "secondary", attrs: "data-tl-close" }) : ""}
      ${submit ? button({ label: submit, variant: danger ? "danger" : "primary", type: "submit" }) : ""}
    </div>
  </form>
</div>`);
    (document.querySelector(".tl-app") || document.body).appendChild(scrim);
    let result = null;
    const done = () => { observer.disconnect(); setTimeout(() => scrim.remove(), 250); resolve(result); };
    const observer = new MutationObserver(() => { if (scrim.hidden) done(); });
    observer.observe(scrim, { attributes: true, attributeFilter: ["hidden"] });
    const form = scrim.querySelector("form");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector("button[type=submit]");
      scrim.querySelector("[data-error]").innerHTML = "";
      setBusy(btn, true, "Working");
      try {
        result = (await onSubmit(form)) ?? true;
        scrim.hidden = true;
      } catch (err) {
        scrim.querySelector("[data-error]").innerHTML = str(alert({ tone: "danger", title: err instanceof ApiError || err instanceof Error ? err.message : "That didn't work." }));
        setBusy(btn, false);
      }
    });
    scrim.hidden = false;
    onOpen?.(scrim);
    (scrim.querySelector("input, select, textarea") || scrim.querySelector("button[type=submit]"))?.focus();
  });
}

/** A yes/no question. Resolves true or false. */
export async function confirmDialog({ title, body, confirm = "Yes", cancel = "Cancel", danger = false, onConfirm }) {
  return !!(await formDialog({ title, intro: body, submit: confirm, cancel, danger, onSubmit: async () => { await onConfirm?.(); return true; } }));
}

/** Show something that can't be a form, like a code to copy. */
export function infoDialog({ title, body, close = "Done", onOpen }) {
  return formDialog({ title, body, submit: close, cancel: null, onSubmit: async () => true, onOpen });
}
