// The plain-language privacy notes: ONE source for the setup screen (before a parent agrees), the app's Privacy and safety
// page, and the public policy at /privacy/ (the link Google's sign-in setup asks for). Change the words here only.
import { CONTACT, html, icon } from "/shared/ui.js";

export const PRIVACY_UPDATED = "November 2026";

export const PRIVACY_QA = [
  ["Can Treeline call 911 or outside numbers?",
    ["No. Treeline connects treehouses to treehouses, nothing else. Outside numbers can't call in either. Kids need another way to reach help."]],
  ["Who can my kids call?",
    ["Only treehouses you're strung with, where both families said yes. Nobody else can ring your phones, and there are no caller names or announcements."]],
  ["Can I listen to calls?",
    ["No. Treeline never records or listens to what's said on a call."]],
  ["What does Treeline store?",
    ["Your email address and name; your treehouse's name, number and rules; the names of your phones; your strings; and a record of every call attempt: who, when, how long and how it ended. Parent actions, like approving a string, are logged too."]],
  ["What does Treeline get from Google?",
    ["When you sign in with Google, Treeline receives only your email address and the fact that Google has verified it. Treeline never sees your Google password, your contacts, or anything else in your Google account."]],
  ["How long is it kept?",
    ["Call records are kept for 90 days unless you choose a different time in Settings (7 days to a year). The action log is kept for a year. Backups are deleted after 7 days."]],
  ["Who can see it?",
    ["Only the grown-ups in your treehouse. A family you're strung with sees the calls between your two treehouses: name, number, time and length. They never see your quiet hours or limits, or why a call to you didn't connect."]],
  ["Where is it kept, and who helps run Treeline?",
    ["On Treeline's server at Amazon Web Services in the United States (Oregon). Backups are encrypted before they leave the server, and only Treeline's maintainer holds the key to open them.",
     "Alert emails are sent through Amazon's email service. Notifications on your phone go through your browser's own push service. Sign-in goes through Google."]],
  ["Does Treeline sell or share it?",
    ["No. There are no ads, no tracking and no analytics. Your information is used only to run Treeline, and shared only with the services above for that purpose."]],
  ["How do I delete it?",
    ["Settings, then Delete everything. That erases your treehouse, phones, strings and call records at once; encrypted backups of them are gone within 7 days. Other families keep their side of past calls, without your name."]],
  ["What about children's privacy rules?",
    ["Kids never have an account or give Treeline any information: only parents sign in. If Treeline grows beyond friends and neighbors, we'll get legal advice about children's privacy laws, like COPPA, before inviting more families."]],
  ["Questions, or a request about your information?",
    [`Email Treeline's maintainer at ${CONTACT}. You can ask what Treeline holds about you, or ask for it to be corrected or deleted.`]],
];

const q = (summary, paras) => html`<details class="tl-disclosure"><summary><span>${summary}</span>${icon("chevron-down")}</summary><div class="tl-disclosure__body">${paras.map((p) => html`<p>${p}</p>`)}</div></details>`;

/** Folded questions, for the setup screen and the app's Privacy and safety page. */
export function privacyAccordion() {
  return html`<div class="tl-accordion">${PRIVACY_QA.map(([summary, paras]) => q(summary, paras))}</div>`;
}

/** The same notes, all open, as a document: the public policy page. */
export function privacyDocument() {
  return html`${PRIVACY_QA.map(([question, paras]) => html`<section class="tl-stack tl-stack--related">
    <h2 class="title-lg">${question}</h2>${paras.map((p) => html`<p class="tl-measure">${p}</p>`)}</section>`)}`;
}
