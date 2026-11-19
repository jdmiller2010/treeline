// The one place the installed app starts. It opens in whichever mode this device is in:
//   - a phone (this device has a softphone sign-in)        -> the rotary phone
//   - a parent signed in, not a phone                      -> the parent dashboard
//   - neither                                              -> the first screen: the QR code to add this softphone, and Log in
import { appHome, registerApp } from "/shared/pwa.js";

registerApp();
location.replace(appHome());
