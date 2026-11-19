// The parent code: 4 to 6 digits a parent sets once. It is what lets a grown-up take a device out of phone mode, and it has to
// exist before the first softphone is added. The server keeps only a salted hash, and locks the code after five wrong tries.
import { put } from "/shared/api.js";
import { html, textField, toast } from "/shared/ui.js";
import { formDialog } from "./dialogs.js";

const DIGITS = { inputmode: "numeric", pattern: "[0-9]*", maxlength: "6", autocomplete: "off" };

export const hasParentCode = (ctx) => !!ctx.me.treehouse.has_parent_code;

/** One code box: digits only, hidden as you type (a child may be looking). */
export const codeBox = ({ id, name, label, hint }) => textField({ id, name, label, hint, type: "password", attrs: DIGITS });

/** The two boxes for choosing a new code (the code, then again), to sit inside any form. */
export function newCodeFields(prefix = "pc") {
  return html`${codeBox({ id: `${prefix}-new`, name: "pin", label: "Parent code", hint: "4 to 6 digits. A parent types it to take a device out of phone mode." })}
  ${codeBox({ id: `${prefix}-again`, name: "pin2", label: "Parent code again" })}`;
}

/** Read the two boxes from a form, check them, and save the code. Throws a message to show in the form. */
export async function saveNewCode(ctx, form, current) {
  const code = form.querySelector("[name=pin]").value.trim(), again = form.querySelector("[name=pin2]").value.trim();
  if (!/^\d{4,6}$/.test(code)) throw new Error("Use 4 to 6 digits for the parent code.");
  if (code !== again) throw new Error("The two codes don't match.");
  ctx.me.treehouse = await put("/api/treehouse/parent-code", { code, ...(current ? { current } : {}) });
}

/** Settings: set the code, or change it (the current one is asked for first). */
export async function parentCodeDialog(ctx) {
  const change = hasParentCode(ctx);
  const done = await formDialog({
    title: change ? "Change the parent code" : "Set a parent code",
    intro: change ? "Type the current code, then choose a new one."
      : "This code lets a parent take a device out of phone mode. Set it before you add a softphone, and don't share it with the kids.",
    submit: change ? "Change code" : "Set code",
    body: html`${change ? codeBox({ id: "pc-current", name: "current", label: "Current code", hint: "Forgot it? Sign out and sign in again, then leave this empty." }) : ""}${newCodeFields()}`,
    onSubmit: (f) => saveNewCode(ctx, f, change ? f.querySelector("[name=current]").value : undefined),
  });
  if (done) toast(change ? "The parent code was changed" : "The parent code is set", "success");
  return !!done;
}
