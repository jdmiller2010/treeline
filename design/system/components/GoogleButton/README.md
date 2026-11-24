# GoogleButton

The Sign in with Google button, the one people already know: white, a grey hairline, Google's four-colour "G" and the words "Sign in with Google".

**Consumer provides:** what happens on click (send the browser to `/api/auth/google/start`). Build it with `googleButton()` from `web/shared/ui.js`.

- It follows Google's sign-in branding guidelines, not our tokens: `#fff` with a `#747775` hairline and `#1f1f1f` text in light, `#131314` with `#8e918f` and `#e3e3e3` in dark. The G is never recoloured, cropped or shown on its own.
- It is the page's main action, so the page has no other primary button. On the sign-in card it shares one row with "Use as a phone": the two grow to fill the card's width together (lined up with the title and the Closed beta tag), never stacked as full-width bars.
- The label is "Sign in with Google" (Google's own wording). On a phone (480px and under) it shortens to "Sign in", Google's own short label, so it fits beside "Use as a phone"; its `aria-label` keeps the full words. The type is our interface face at 500: Google asks for Roboto Medium, which Treeline doesn't ship.
- Only on the sign-in card (`.tl-login`: "Log in to Treeline" with a "Closed beta" tag at the right of the title, then Google's button with the secondary "Use as a phone" beside it at the same height, then the no-911 line).

## HTML

See `ui/components/GoogleButton.html`.
