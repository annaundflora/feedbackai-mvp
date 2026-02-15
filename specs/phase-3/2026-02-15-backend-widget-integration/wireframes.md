# Wireframes: Backend-Widget-Integration

**Discovery:** `discovery.md` (same folder)
**Status:** Draft

---

## Component Coverage

| UI Component (from Discovery) | Screen |
|-------------------------------|--------|
| `FloatingButton` | All Screens (persistent) |
| `Panel` | All Screens (container) |
| `PanelHeader` | Consent, Chat, ThankYou |
| `ConsentScreen` | Consent |
| `ChatScreen` | Chat |
| `ChatThread` | Chat |
| `ChatMessage (User)` | Chat |
| `ChatMessage (Assistant)` | Chat |
| `ChatComposer` | Chat |
| `LoadingIndicator` | Chat (during /start) |
| `TypingIndicator` | Chat (during streaming) |
| `ErrorDisplay` | Chat (error states) |
| `ThankYouScreen` | ThankYou |

---

## User Flow Overview

```
[Host Page Load]
      │
      └──► [Floating Button visible]
               │
               └──click──► [Consent Screen]
                              │
                              └──"Los geht's"──► [Chat Screen + Loading]
                                                      │
                                                      └──/start SSE──► [Assistant Message]
                                                                           │
                                                                           └──user types──► [User Message]
                                                                                               │
                                                                                               └──/message SSE──► [Assistant Response]
                                                                                                                      │
                                                                                                                      ├──repeat 3-10x
                                                                                                                      │
                                                                                                                      └──close panel──► [ThankYou Screen]
                                                                                                                                           │
                                                                                                                                           └──auto-close 5s──► [Closed]

[Error occurs] ──► [Error Display + Retry]
```

---

## Screen: Consent Screen (Existing from Phase 2)

**Context:** First screen after clicking Floating Button. Panel slides up (300ms animation). Focus on user consent for anonymous interview.

**New Behavior (Phase 3):** Clicking "Los geht's" now triggers `/api/interview/start` API call with anonymous_id.

### Wireframe

```
┌─────────────────────────────────────────┐  ← ① Panel (384px×600px)
│  Feedback-Interview                  ② │  ← ② PanelHeader
│                                         │
│                                         │
│          💬                             │
│                                         │
│      Ihre Meinung zählt           ③   │  ← ③ Headline
│                                         │
│   Wir möchten gerne Ihr Feedback zu    │
│   unseren Services erhalten. Das       │
│   Interview ist anonym und dauert      │  ← ④ Body Text
│   etwa 2-3 Minuten.                    │
│                                         │
│   Ihre Antworten helfen uns, unsere    │
│   Leistungen kontinuierlich zu         │
│   verbessern.                          │
│                                         │
│                                         │
│   ┌──────────────────────────────┐    │
│   │      Los geht's         ⑤    │    │  ← ⑤ CTA Button
│   └──────────────────────────────┘    │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `Panel`: Main container, slides up from bottom
- ② `PanelHeader`: Title + X-Button (top-right)
- ③ `Headline`: "Ihre Meinung zählt"
- ④ `Body Text`: Consent explanation + data privacy info
- ⑤ `CTA Button`: "Los geht's" - triggers anonymous_id generation + /start API

### State Variations

| State | Visual Change |
|-------|---------------|
| `initial` | Default view, button enabled |
| `loading` | (Not shown here - transitions to Chat Screen) |

---

## Screen: Chat Screen - Initial State (Loading)

**Context:** After clicking "Los geht's". Anonymous-ID generated, /start API called. Waiting for first response from backend.

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │  ← ① PanelHeader (with X-Button)
├─────────────────────────────────────────┤
│                                         │
│                                         │
│                                         │
│                                         │
│             ⚪                           │
│         Verbinde...              ②    │  ← ② LoadingIndicator (pulsing)
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [                            ]  ③  │   │  ← ③ ChatComposer (disabled)
│                              │Send│    │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Title "Feedback-Interview" + X-Button
- ② `LoadingIndicator`: "Verbinde..." with pulse animation (opacity 0.5 → 1.0)
- ③ `ChatComposer`: Input field + Send button (disabled, grey)

### State Variations

| State | Visual Change |
|-------|---------------|
| `CONNECTING` | LoadingIndicator visible, Composer disabled |
| `metadata_received` | LoadingIndicator still visible (waiting for first text-delta) |

---

## Screen: Chat Screen - Assistant Streaming (First Response)

**Context:** SSE metadata received, session_id stored. First text-deltas arriving. Typing indicator appears before first delta, then replaced by actual message text.

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │
├─────────────────────────────────────────┤
│                                         │
│ ●  ┌────────────────────────────┐      │
│    │ ...                    ②  │      │  ← ② TypingIndicator (before first delta)
│    └────────────────────────────┘      │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [                            ]  ③  │   │  ← ③ ChatComposer (disabled)
│                              │Send│    │
└─────────────────────────────────────────┘

          ↓ First text-delta arrives ↓

┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │
├─────────────────────────────────────────┤
│                                         │
│ ●  ┌────────────────────────────┐      │
│ ④ │ Hallo! Vielen Dank, dass   │      │  ← ④ Assistant-Message (streaming)
│    │ Sie sich Zeit nehm▊         │      │     Text appends progressively
│    └────────────────────────────┘      │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [                            ]  ③  │   │  ← ③ ChatComposer (still disabled)
│                              │Send│    │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Unchanged
- ② `TypingIndicator`: "..." with bounce animation (translateY -4px → 0px, staggered)
- ③ `ChatComposer`: Disabled during streaming (grey, disabled attribute)
- ④ `Assistant-Message`: Left-aligned, grey-100 background, grey-900 text, max 80% width, optional avatar (●)

### State Variations

| State | Visual Change |
|-------|---------------|
| `ASSISTANT_STREAMING` (before first delta) | TypingIndicator visible |
| `ASSISTANT_STREAMING` (after first delta) | TypingIndicator replaced by message, text appends |
| `text-done` | Composer enabled, cursor blinks in input field |

---

## Screen: Chat Screen - Chat History (After Exchange)

**Context:** User has sent 1-2 messages, Assistant has responded. Chat thread shows alternating user/assistant messages. Composer is enabled.

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │
├─────────────────────────────────────────┤
│                                         │
│ ●  ┌────────────────────────────┐      │
│    │ Hallo! Vielen Dank, dass   │      │
│    │ Sie sich Zeit nehmen. Wie  │      │  ← ② Assistant-Message (complete)
│    │ würden Sie unseren Service │      │
│    │ beschreiben?                │      │
│    └────────────────────────────┘      │
│                                         │
│                   ┌──────────────────┐ │
│                   │ Sehr gut! Die    │ │
│                   │ Plattform ist    │ │  ← ③ User-Message
│                   │ einfach zu       │ │     (right-aligned, brand-color)
│                   │ bedienen.        │ │
│                   └──────────────────┘ │
│                                         │
│ ●  ┌────────────────────────────┐      │
│    │ Das freut mich zu hören!   │      │
│    │ Was gefällt Ihnen am       │      │  ← ④ Assistant-Message
│    │ besten?                     │      │
│    └────────────────────────────┘      │
│                                         │
├─────────────────────────────────────────┤
│ [ Hier tippen...         ]  ⑤  │ ⑥ │   │  ← ⑤ Input (enabled)
│                              │Send│    │  ← ⑥ Send Button
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Unchanged
- ② `Assistant-Message`: Left-aligned, grey-100 background, text complete (no streaming)
- ③ `User-Message`: Right-aligned, brand-color background (#3B82F6), white text, max 80% width
- ④ `Assistant-Message`: Next response in conversation
- ⑤ `ChatComposer Input`: Enabled, placeholder "Hier tippen...", white background
- ⑥ `Send Button`: Enabled when input not empty, brand-color

### State Variations

| State | Visual Change |
|-------|---------------|
| `WAITING_USER_INPUT` | Composer enabled, cursor blinking |
| `SENDING_MESSAGE` | Composer disabled, User-Message appears immediately |
| `input_empty` | Send button disabled/hidden |

---

## Screen: Chat Screen - Error Display

**Context:** Network error, timeout, or backend error occurred. Error-Display component appears below last message with error details and retry option.

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │
├─────────────────────────────────────────┤
│                                         │
│ ●  ┌────────────────────────────┐      │
│    │ Hallo! Vielen Dank, dass   │      │
│    │ Sie sich Zeit nehmen...     │      │
│    └────────────────────────────┘      │
│                                         │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│ ┃ ⚠️  Verbindung fehlgeschlagen  ②  ┃  │  ← ② ErrorDisplay
│ ┃                                    ┃  │     (red border, red-50 background)
│ ┃ Bitte Netzwerk prüfen und erneut  ┃  │
│ ┃ versuchen.                         ┃  │
│ ┃                                    ┃  │
│ ┃  ┌──────────────────┐       ③   │  │  ← ③ Retry Button
│ ┃  │ Erneut versuchen  │            ┃  │
│ ┃  └──────────────────┘             ┃  │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [                            ]  ④  │   │  ← ④ ChatComposer (disabled)
│                              │Send│    │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Unchanged
- ② `ErrorDisplay`: Red-50 background, red-700 border, ⚠️ icon, error message text (red-900)
- ③ `Retry Button`: "Erneut versuchen" - triggers retry logic (re-/start or re-/message)
- ④ `ChatComposer`: Disabled during error state

### State Variations

| State | Visual Change |
|-------|---------------|
| `ERROR` (Network) | "Verbindung fehlgeschlagen. Bitte Netzwerk prüfen..." |
| `ERROR` (Timeout) | "Zeitüberschreitung. Server antwortet nicht." |
| `ERROR` (Session Expired) | "Sitzung abgelaufen." + "Neu starten" button |
| `ERROR` (Server Error) | "Ein Fehler ist aufgetreten. Bitte später versuchen." |
| `ERROR` (Stream Abort) | "Verbindung unterbrochen." + partial message remains visible |

---

## Screen: Chat Screen - Session Expired Error

**Context:** User returns after 60s timeout or sends message to expired session. Special error case with "Neu starten" button instead of "Retry".

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │
├─────────────────────────────────────────┤
│                                         │
│ ●  ┌────────────────────────────┐      │
│    │ [... previous messages ...]│      │
│    └────────────────────────────┘      │
│                                         │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│ ┃ ⚠️  Sitzung abgelaufen         ②  ┃  │  ← ② ErrorDisplay (404 Error)
│ ┃                                    ┃  │
│ ┃ Ihre Interview-Sitzung ist         ┃  │
│ ┃ abgelaufen. Möchten Sie ein neues  ┃  │
│ ┃ Interview starten?                 ┃  │
│ ┃                                    ┃  │
│ ┃  ┌──────────────────┐       ③   │  │  ← ③ "Neu starten" Button
│ ┃  │   Neu starten     │            ┃  │     (returns to Consent Screen)
│ ┃  └──────────────────┘             ┃  │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                         │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ [                            ]     │   │  ← Composer disabled
│                              │Send│    │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Unchanged
- ② `ErrorDisplay`: Session expired message (404 from backend)
- ③ `Neu starten Button`: Clears session_id, resets state to IDLE, returns to Consent Screen

---

## Screen: ThankYou Screen (Existing from Phase 2)

**Context:** Interview completed. User closed panel or clicked end button. `/api/interview/end` called, summary received. Auto-close timer starts (5 seconds).

**New Behavior (Phase 3):** Now triggered after `/api/interview/end` API call completes.

### Wireframe

```
┌─────────────────────────────────────────┐
│  Feedback-Interview                  ① │  ← ① PanelHeader
├─────────────────────────────────────────┤
│                                         │
│                                         │
│                                         │
│            ✓                            │  ← ② Success Icon (green)
│                                         │
│       Vielen Dank!              ③      │  ← ③ Headline
│                                         │
│     Ihr Feedback hilft uns,            │
│     unsere Leistungen zu               │  ← ④ Body Text
│     verbessern.                        │
│                                         │
│                                         │
│     Dieses Fenster schließt sich       │
│     automatisch in 5 Sekunden...  ⑤   │  ← ⑤ Auto-Close Info
│                                         │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

**Annotations:**
- ① `PanelHeader`: Title (no X-Button during auto-close)
- ② `Success Icon`: Green checkmark (✓)
- ③ `Headline`: "Vielen Dank!"
- ④ `Body Text`: Confirmation message
- ⑤ `Auto-Close Info`: Timer countdown (5 seconds)

### State Variations

| State | Visual Change |
|-------|---------------|
| `COMPLETED` | Auto-close timer running (5s countdown) |
| `auto_close` | Panel slides down, screen resets to `consent`, session_id cleared |

---

## Screen: Floating Button (Persistent)

**Context:** Persistent button in bottom-right corner of host page. Visible at all times. Opens panel on click.

### Wireframe

```
[... Host Page Content ...]

                                          ┌────┐
                                          │ 💬 │  ← Floating Button
                                          │    │     (bottom-right, fixed)
                                          └────┘
                                            ①
```

**Annotations:**
- ① `FloatingButton`: 56×56px, brand-color background, white icon (💬), box-shadow, pulse animation on first load

### State Variations

| State | Visual Change |
|-------|---------------|
| `panel_closed` | Button visible with pulse animation |
| `panel_open` | Button remains visible (can be clicked to close) |

---

## Completeness Check

| Check | Status |
|-------|--------|
| All UI Components from Discovery covered | ✅ |
| All relevant states visualized | ✅ |
| Loading states (CONNECTING, ASSISTANT_STREAMING) | ✅ |
| Error states (Network, Timeout, Session Expired) | ✅ |
| User Flow (Consent → Chat → ThankYou) | ✅ |
| New components (LoadingIndicator, TypingIndicator, ErrorDisplay, Assistant-Message) | ✅ |
| Existing components (FloatingButton, ConsentScreen, ThankYouScreen) documented | ✅ |
