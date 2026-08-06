# UI-UX.md — Two-Pane Demo Interface

## Layout

```text
+------------------------+-------------------------------+
|      CHAT PANE          |       SOURCE VIEWER PANE       |
| (left, ~40% width)      | (right, ~60% width)            |
|                          |                                |
| [question input box]    |  PDF page render, page N        |
|                          |  highlighted region = active    |
| --- answer bubble ---   |  citation quote                 |
| "The notice period is   |                                |
|  30 days."               |  [page nav: << 12 >>]           |
|                          |                                |
| [Citation chip: p.12,   |                                |
|  Sec 4.2] <- clickable   |                                |
+------------------------+-------------------------------+
```

## Interaction Flow

1. User types a question, hits enter / clicks send.
2. Loading state on the chat pane only (source pane stays as-is until
   an answer resolves — don't blank it, it's disorienting).
3. **Answered case:** answer text renders as a chat bubble. Below it,
   one citation chip per surviving citation, formatted
   `p.{page} — {section}`. Clicking a chip scrolls the source viewer
   to that page and highlights the matched quote span.
4. **Refused case:** distinct visual treatment — NOT a red error
   box. Use a neutral/informational style (e.g. a small icon +
   "Not found in the provided documents" framing). This is a correct
   behavior, and the UI should not make it look like something broke.
   This distinction matters for the demo: judges should be able to
   tell at a glance "refusal" apart from "bug."

## Component List (keep this list short — this is 48 hours, not a
## design system)

- `ChatPane` — input, message list, loading state
- `AnswerBubble` — renders answer text + citation chips
- `RefusalBubble` — visually distinct from AnswerBubble, same
   component family for layout consistency
- `CitationChip` — clickable, `p.{page} — {section}` label
- `SourceViewer` — renders current page (PDF.js or similar), accepts
   a highlight region prop
- `PageNav` — simple prev/next, page number, no thumbnail rail (cut
   for time — see below)

## Explicitly Cut From UI Scope (do not build these)

- Document upload drag-and-drop polish — a plain file input is fine,
  judges care about the answer/citation loop, not the upload UX.
- Multi-document tabs — single active document set for the demo is
  enough (DECISION.md deferred list).
- Chat history persistence across page reloads — in-memory state for
  the session is enough.
- Confidence score badges, "fast path vs reasoned" indicators, or any
  other KRE-style UI chrome — this system has one path, not two, so
  there's nothing to badge (BOUNDARIES.md).
- Dark/light theme toggle, animations beyond basic loading states.

## Demo Script Alignment

The UI's entire job is to make the guardrail visible in real time:
question in -> citation chip out (or honest refusal) -> click to
verify. If a UI element doesn't serve that loop, it's not worth
building in this window. Refer back here before adding anything not
on the component list above.
