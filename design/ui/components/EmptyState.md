# EmptyState

A calm, centered moment for screens with nothing in them yet: an illustration, a title, one sentence, and at most one action.

**Consumer provides:** `illustration` (an Illustration name, default `treehouse`), `title`, `children` (one or two short sentences), optional `action` (usually a primary Button).

- Write what's possible, not what's missing: "Invite a friend to the treehouse", not "No contacts found".
- Title in Fraunces; body in `ink-muted`; lots of open space above (`space-12`).
- One primary action at most. If there's nothing to do, leave it out.

## HTML

Exact markup for use without React, with `tokens.css` and `components/bundle.css`. Keep the classes and nesting; change text, ids, links and labels.

**Treehouse**

```html
<section class="tl-card">
  <div class="tl-empty">
    <div class="tl-empty__art">
      <svg class="tl-art" viewBox="0 0 240 180" style="width:100%;height:auto" aria-hidden="true"><path class="w-sky" d="M228.0 58.0C228.2 69.3 230.2 84.3 218.5 92.1C206.9 100.0 176.6 106.1 158.0 105.2C139.4 104.4 119.6 94.9 106.6 87.0C93.6 79.1 80.6 67.9 80.1 58.0C79.6 48.1 90.6 35.0 103.6 27.3C116.6 19.7 139.0 12.6 158.0 12.1C177.0 11.6 205.9 16.7 217.6 24.4C229.3 32.0 227.9 46.7 228.0 58.0Z"/><circle class="w-sun" cx="196" cy="34" r="15"/><path class="w-leaf" d="M200.4 66.0C201.8 76.7 190.9 94.6 178.5 101.0C166.1 107.4 141.6 105.8 126.0 104.5C110.4 103.3 96.8 99.9 84.8 93.5C72.7 87.1 55.2 76.1 53.8 66.0C52.4 55.9 64.2 40.5 76.2 32.8C88.3 25.1 110.3 19.3 126.0 19.9C141.7 20.5 157.8 28.9 170.2 36.6C182.6 44.2 199.0 55.3 200.4 66.0Z"/><path class="w-bark" d="M155.5 118.0C155.2 121.0 153.6 124.7 148.3 126.6C143.1 128.5 132.2 129.5 124.0 129.6C115.8 129.6 105.1 128.7 99.3 126.7C93.4 124.8 88.2 120.7 88.8 118.0C89.4 115.3 97.0 112.3 102.9 110.5C108.7 108.8 116.1 107.9 124.0 107.6C131.9 107.3 145.1 107.0 150.3 108.7C155.6 110.4 155.8 115.0 155.5 118.0Z"/><path class="ln" d="M85.6 98.1A18.0 18.0 0 0 1 61.9 78.6A8.6 8.6 0 0 1 55.9 66.5A21.6 21.6 0 0 1 67.1 37.6A21.8 21.8 0 0 1 95.5 25.2A10.0 10.0 0 0 1 112.3 19.3A32.7 32.7 0 0 1 158.7 27.4A17.2 17.2 0 0 1 179.9 42.8A11.2 11.2 0 0 1 185.3 59.9A12.8 12.8 0 0 1 178.3 80.9A20.3 20.3 0 0 1 154.7 98.5"/><path class="ln" d="M114 116C113 132 110 146 104 160M128 116C129 132 132 146 138 160"/><path class="ln-soft" d="M100 100C96 94 90 90 82 88M142 100C148 92 156 88 164 88"/><path class="ln" d="M97.0 116H147.0"/><path class="ln" d="M105.0 116V100H139.0V116"/><path class="ln" d="M101.0 101L122 88L143.0 101"/><path class="ln" d="M118 116V107H126V116"/><path class="ln" d="M92 116L88 160M101 116L98 160"/><path class="ln-soft" d="M90.6 128H99.8M89.6 140H98.8M88.6 152H97.8"/><path class="ln-soft" d="M56 160C100 156 152 156 200 160"/><path class="w-leaf" transform="translate(187.6 119.2) rotate(40) scale(0.8400000000000001)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="ln" transform="translate(186 118) rotate(40) scale(0.8)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/><path class="w-leaf" transform="translate(205.6 141.2) rotate(-20) scale(0.735)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10Z"/><path class="ln" transform="translate(204 140) rotate(-20) scale(0.7)" d="M0 -10C6 -5 6 5 0 10C-6 5 -6 -5 0 -10ZM0 -8V8"/></svg>
    </div>
    <h3 class="tl-empty__title">Your treehouse is ready</h3>
    <p class="tl-empty__body">Add a friend from the park, and Sam can call them once both families say yes.</p>
    <div class="tl-empty__action">
      <button type="button" class="tl-btn tl-btn--primary tl-btn--md">
        <svg class="tl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3v18M16 3v18M8 7.5h8M8 12h8M8 16.5h8"/></svg>
        <span class="tl-btn__label">Invite a friend</span>
      </button>
    </div>
  </div>
</section>
```
