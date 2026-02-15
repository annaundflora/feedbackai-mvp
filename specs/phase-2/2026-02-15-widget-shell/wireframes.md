# Wireframes: Widget-Shell

**Discovery:** `discovery.md` (same folder)
**Status:** Draft

---

## Component Coverage

| UI Component (from Discovery) | Screen |
|-------------------------------|--------|
| `floating-button` | Floating Button |
| `panel` | Panel Container |
| `panel-header` | Panel Container |
| `close-button` | Panel Container |
| `consent-cta` | Consent Screen |
| `chat-thread` | Chat Screen |
| `chat-composer` | Chat Screen |

---

## User Flow Overview

```
[Panel Closed] ──click bubble──► [Panel Open: Consent]
                                       │
                                       ├──click "Los geht's"──► [Panel Open: Chat]
                                       │                              │
                                       │                    (Phase 3: interview ends)
                                       │                              │
                                       │                              ▼
                                       │                    [Panel Open: Danke]
                                       │                         │         │
                                       │               (auto 5s) │         │ (click X)
                                       │                         ▼         ▼
                                       │                    [Panel Closed: Reset to Consent]
                                       │
                                       └──click X──► [Panel Closed: Screen preserved]
```

---

## Screen: Floating Button (Panel Closed)

**Context:** Fixed bottom-right corner of host page. Always visible when panel is closed.

### Wireframe

```
[... host page content ...]

                                          ┌──────┐
                                          │  ①   │
                                          │ (💬) │
                                          └──────┘
                                            16px ─┤
                                                  │
                                            16px ─┘
```

**Annotations:**
- ① `floating-button`: Round button (48-56px), chat-bubble SVG icon, white on dark background. Click opens panel.

### State Variations

| State | Visual Change |
|-------|---------------|
| `default` | Button visible at bottom-right |
| `hover` | Slight scale animation |
| `panel open` | Button hidden |

---

## Screen: Panel Container (Open)

**Context:** Fixed overlay, bottom-right. Desktop ~400x600px. Replaces floating button when open.

### Wireframe — Desktop

```
[... host page content ...]

                        ┌──────────────────────────────┐
                        │ ②  Widget-Titel          ③ X │
                        ├──────────────────────────────┤
                        │                              │
                        │                              │
                        │                              │
                        │     ④  Screen Content        │
                        │     (Consent / Chat / Danke) │
                        │                              │
                        │                              │
                        │                              │
                        │                              │
                        │                              │
                        └──────────────────────────────┘
                                                  16px ─┤
                                                        │
                                                  16px ─┘
```

**Annotations:**
- ② `panel-header`: Title text left-aligned
- ③ `close-button`: X button, top-right in header. Closes panel, screen state preserved.
- ④ `panel`: Body area, renders current screen content

### Wireframe — Mobile (<=768px)

```
┌──────────────────────────────────────────┐
│ ②  Widget-Titel                     ③ X │
├──────────────────────────────────────────┤
│                                          │
│                                          │
│                                          │
│                                          │
│          ④  Screen Content               │
│          (Consent / Chat / Danke)        │
│                                          │
│                                          │
│                                          │
│                                          │
│                                          │
│                                          │
└──────────────────────────────────────────┘
```

### State Variations

| State | Visual Change |
|-------|---------------|
| `open` | Panel visible with slide-up animation (300ms) |
| `closed` | Panel hidden with slide-down animation (300ms), floating button reappears |

---

## Screen: Consent

**Context:** First screen shown inside panel body when user opens widget.

### Wireframe

```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│    ① Ihr Feedback zaehlt!    │
│                              │
│    ② Wir moechten Ihnen      │
│    ein paar kurze Fragen     │
│    stellen. Dauert ca.       │
│    5 Minuten.                │
│                              │
│                              │
│  ┌──────────────────────┐    │
│  │  ③ Los geht's        │    │
│  └──────────────────────┘    │
│                              │
└──────────────────────────────┘
```

**Annotations:**
- ① Headline text (configurable)
- ② Intro/description text (configurable)
- ③ `consent-cta`: Full-width button at bottom of panel. Click transitions to chat screen.

### State Variations

| State | Visual Change |
|-------|---------------|
| `default` | As shown above |
| `hover (CTA)` | Button hover state |

---

## Screen: Chat

**Context:** Shown after user accepts consent. Contains @assistant-ui/react primitives.

### Wireframe

```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│                              │
│    ①  (empty message list)   │
│                              │
│                              │
│                              │
│                              │
│                              │
├──────────────────────────────┤
│ ② [Type a message...]   [➤] │
└──────────────────────────────┘
```

**Annotations:**
- ① `chat-thread`: @assistant-ui Thread with MessageList. Phase 2: empty. Phase 3: live chat messages.
- ② `chat-composer`: @assistant-ui Composer input field, always visible and open. Phase 2: no backend connection.

### State Variations

| State | Visual Change |
|-------|---------------|
| `empty` (Phase 2) | Empty message list, composer visible |
| `active` (Phase 3) | Messages in list, composer functional |
| `typing` | User typing in composer |

---

## Screen: Danke (Thank You)

**Context:** Shown after interview ends (Phase 3+). Auto-closes panel after ~5 seconds.

### Wireframe

```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│                              │
│    ① Vielen Dank!            │
│                              │
│    ② Ihr Feedback hilft      │
│    uns, besser zu werden.    │
│                              │
│                              │
│                              │
│                              │
│                              │
└──────────────────────────────┘
```

**Annotations:**
- ① Headline text (configurable)
- ② Thank you message text (configurable)

### State Variations

| State | Visual Change |
|-------|---------------|
| `default` | As shown, auto-close timer running |
| `closing` | Panel slides down after ~5s, resets screen to consent |

---

## Completeness Check

| Check | Status |
|-------|--------|
| All UI Components from Discovery covered | ✅ |
| All relevant states visualized | ✅ |
