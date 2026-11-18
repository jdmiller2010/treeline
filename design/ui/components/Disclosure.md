# Disclosure

A heading that opens to show more: help answers, advanced settings.

**Consumer provides:** `title`, `children`, optional `defaultOpen`. Group several in an `Accordion`.

- A native `<details>` and `<summary>`, so it works without JavaScript and with the keyboard. The title is 16px semibold with a chevron on the right that turns when open; the answer is 15/24 `ink-muted`, capped at `reading-max`.
- Hairline rules between items. Inside a Card, the accordion's outer rules drop so the card edge does the job.
- Several can be open at once. Open the first one when it answers the most common question.
- Don't hide anything a parent must see to act safely; that goes in the page.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels. It's native `<details>`, so it needs no JavaScript.

**Single, closed**

```html
<details class="tl-disclosure">
  <summary>
    <span>What if Sam’s phone loses Wi-Fi?</span>
    <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
  </summary>
  <div class="tl-disclosure__body">
    <p>Calls can’t reach it until it reconnects. You’ll see “offline” on Home, and the phone tries again every minute.</p>
  </div>
</details>
```

**Accordion in a card**

```html
<section class="tl-card">
  <div class="tl-accordion">
    <details class="tl-disclosure" open="">
      <summary>
        <span>Who can my kid call?</span>
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
      </summary>
      <div class="tl-disclosure__body">
        <p>Only friends both families approved, plus family you add. Nobody else can ring the phone.</p>
      </div>
    </details>
    <details class="tl-disclosure">
      <summary>
        <span>Can I listen to calls?</span>
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
      </summary>
      <div class="tl-disclosure__body">
        <p>No. Treeline never records calls. You see who called whom, when and for how long.</p>
      </div>
    </details>
    <details class="tl-disclosure">
      <summary>
        <span>How do quiet hours work?</span>
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
      </summary>
      <div class="tl-disclosure__body">
        <p>During quiet hours calls wait. The phone won’t ring, and the caller hears a soft “try later” tone.</p>
      </div>
    </details>
  </div>
</section>
```
