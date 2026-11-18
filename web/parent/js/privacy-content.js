// The plain-language privacy notes, shown in setup (before a parent agrees) and under Privacy and safety.
import { html, icon } from "/shared/ui.js";

const q = (summary, ...paras) => html`<details class="tl-disclosure"><summary><span>${summary}</span>${icon("chevron-down")}</summary><div class="tl-disclosure__body">${paras.map((p) => html`<p>${p}</p>`)}</div></details>`;

export function privacyAccordion() {
  return html`<div class="tl-accordion">
    ${q("Can Treeline call 911 or outside numbers?", "No. Treeline connects treehouses to treehouses, nothing else. Outside numbers can't call in either. Kids need another way to reach help.")}
    ${q("Who can my kids call?", "Only treehouses you're strung with, where both families said yes. Nobody else can ring your phones, and there are no caller names or announcements.")}
    ${q("Can I listen to calls?", "No. Treeline never records or listens to what's said on a call.")}
    ${q("What does Treeline store?", "Your email address and name; your treehouse's name, number and rules; the names of your phones; your strings; and a record of every call attempt: who, when, how long and how it ended. Parent actions, like approving a string, are logged too.")}
    ${q("How long is it kept?", "Call records are kept for 90 days unless you choose a different time in Settings (7 days to a year). The action log is kept for a year. Sign-in codes last 10 minutes.")}
    ${q("Who can see it?", "Only the grown-ups in your treehouse. A family you're strung with sees the calls between your two treehouses: name, number, time and length. They never see your quiet hours or limits, or why a call to you didn't connect.")}
    ${q("How do I delete it?", "Settings, then Delete everything. That erases your treehouse, phones, strings and call records. Other families keep their side of past calls, without your name.")}
    ${q("What about children's privacy rules?", "Kids never have an account or give Treeline any information: only parents sign in. If Treeline grows beyond friends and neighbors, we'll get legal advice about children's privacy laws, like COPPA, before inviting more families.")}
  </div>`;
}
