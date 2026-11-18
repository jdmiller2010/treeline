# Steps

Where you are in a short setup flow, and how much is left.

**Consumer provides:** `steps` (short names), `current` (1-based), optional `label`.

- One bar per step: done steps are filled `canopy`, the current one is half filled, upcoming ones are sunk. Each bar has its numbered name under it; the current name is ink and bold.
- **Under 560px of content** the names fold into one line above the bars ("Step 2 of 4: Add a kid") so it never crowds a phone.
- For 3–5 steps. Put it at the top of the flow's page, under the AppBar, `space-8` above the content. Back and Next live in the page's actions, not in the steps.
- Steps aren't links: going back is the Back button, so a parent never skips a required step.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Setup, step 2**

```html
<nav class="tl-stepsnav" aria-label="Setup progress">
  <p class="tl-steps__summary">Step 2 of 4: Add a kid</p>
  <ol class="tl-steps">
    <li class="tl-steps__item is-done">
      <span class="tl-steps__bar" aria-hidden="true">
      </span>
      <span class="tl-steps__label">Your household</span>
    </li>
    <li class="tl-steps__item" aria-current="step">
      <span class="tl-steps__bar" aria-hidden="true">
      </span>
      <span class="tl-steps__label">Add a kid</span>
    </li>
    <li class="tl-steps__item">
      <span class="tl-steps__bar" aria-hidden="true">
      </span>
      <span class="tl-steps__label">Pair the phone</span>
    </li>
    <li class="tl-steps__item">
      <span class="tl-steps__bar" aria-hidden="true">
      </span>
      <span class="tl-steps__label">Invite a friend</span>
    </li>
  </ol>
</nav>
```
