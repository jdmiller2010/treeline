// The public privacy policy (no sign-in): the same words as the app's Privacy and safety page, from one source.
import { privacyDocument, PRIVACY_UPDATED } from "/parent/js/privacy-content.js";
import { footer, NO_911 } from "/shared/ui.js";

document.getElementById("policy").innerHTML = String(privacyDocument());
document.getElementById("updated").textContent = `Last updated ${PRIVACY_UPDATED}. ${NO_911}`;
document.getElementById("footer").innerHTML = String(footer());
