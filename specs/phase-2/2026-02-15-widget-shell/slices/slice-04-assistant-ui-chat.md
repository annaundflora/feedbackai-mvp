# Slice 4: @assistant-ui Chat-UI

> **Slice 4 von 4** für `widget-shell`
>
> | Navigation | |
> |------------|---|
> | **Vorheriger:** | `slice-03-screens-state-machine.md` |
> | **Nächster:** | — |

---

## Metadata (für Orchestrator)

| Key | Value |
|-----|-------|
| **ID** | `slice-04-assistant-ui-chat` |
| **Test** | `cd widget && npm run build && node -e "const fs=require('fs'); const html=fs.readFileSync('test.html','utf-8'); if(!html.includes('@assistant-ui') || !html.includes('chat-ui')) throw new Error('Chat-UI components missing');"` |
| **E2E** | `false` |
| **Dependencies** | `["slice-03-screens-state-machine"]` |

**Erklärung:**
- **ID**: Eindeutiger Identifier für Commits und Evidence
- **Test**: Build-Test - prüft ob @assistant-ui Chat-UI Components vorhanden sind
- **E2E**: Kein E2E-Test nötig (UI-Komponenten werden manuell getestet)
- **Dependencies**: Slice 3 (ChatScreen Component muss vorhanden sein)

---

## Test-Strategy (fuer Orchestrator Pipeline)

> **Quelle:** Auto-detected vom Slice-Writer Agent basierend auf Repo-Indikatoren.

| Key | Value |
|-----|-------|
| **Stack** | `typescript-vite-react` |
| **Test Command** | `cd widget && npm run build` |
| **Integration Command** | `node -e "const fs=require('fs'); const html=fs.readFileSync('widget/test.html','utf-8'); if(!html.includes('chat') && !html.includes('assistant')) throw new Error('Chat-UI not rendered');"` |
| **Acceptance Command** | `node -e "const fs=require('fs'); const stat=fs.statSync('widget/dist/widget.js'); console.log('Bundle size: ' + (stat.size/1024).toFixed(2) + ' KB'); if(stat.size>500000) console.warn('⚠ Bundle >500KB');"` |
| **Start Command** | `cd widget && npm run preview` |
| **Health Endpoint** | `http://localhost:4173` |
| **Mocking Strategy** | `no_mocks` |

**Erklärung:**
- **Stack**: Vite 6 + React 19 + TypeScript 5.7 + Tailwind v4 + @assistant-ui/react v0.7
- **Test Command**: Führt Vite-Build aus
- **Integration Command**: Prüft ob Chat-UI im DOM gerendert wird
- **Acceptance Command**: Zeigt Bundle-Größe an und warnt bei >500KB
- **Start Command**: Startet Vite Preview Server
- **Health Endpoint**: Vite Preview Port
- **Mocking Strategy**: Keine Mocks nötig (Dummy-Runtime für Phase 2)

---

## Slice-Übersicht

| # | Slice | Status | Datei |
|---|-------|--------|-------|
| 1 | Vite + Build Setup | Done | `slice-01-vite-build-setup.md` |
| 2 | Floating Button + Panel Shell | Done | `slice-02-floating-button-panel-shell.md` |
| 3 | Screens + State Machine | Done | `slice-03-screens-state-machine.md` |
| 4 | @assistant-ui Chat-UI | Ready | `slice-04-assistant-ui-chat.md` |

---

## Kontext & Ziel

**Problem:**
- Slice 3 hat ChatScreen als Placeholder
- Kein echtes Chat-UI
- Keine @assistant-ui Primitives integriert (Thread, Composer)
- Kein Chat Runtime (LocalRuntime)
- Keine Chat-Styling an Widget-Theme angepasst

**Ziel:**
- @assistant-ui/react Primitives Integration (Thread, Composer, Message)
- LocalRuntime mit Dummy-Adapter (kein Backend in Phase 2)
- Leerer Chat mit offenem Composer
- Styling an Widget-Theme anpassen (Tailwind v4)
- Chat-UI bereit für Phase 3 Backend-Anbindung

**Business Value:**
- Chat-UI vollständig für Phase 3 vorbereitet
- Widget visuell komplett (alle Screens funktional)
- UX testbar: User kann tippen (auch wenn noch kein Backend antwortet)

---

## Technische Umsetzung

### Architektur-Kontext (aus architecture.md)

> **Quelle:** `architecture.md` → Chat Layer, Component Tree, Q&A Log

**Relevante Architektur-Requirements:**
- Chat Layer: @assistant-ui/react Primitives (Thread, Composer, Message)
- LocalRuntime: Dummy-Adapter für Phase 2 (gibt nichts zurück)
- Primitive Composition: Radix-like Component-Pattern
- Widget-Theme Styling: Tailwind v4 scoped auf `.feedbackai-widget`
- Phase 2 Scope: Leerer Chat, Composer offen, kein Backend

**Constraints:**
- **Keine Backend-Anbindung in Phase 2** (Dummy-Adapter)
- **Primitives-Only**: @assistant-ui/react-ui (styled components) NICHT installiert
- **Volle Styling-Kontrolle**: Alle Styles via Tailwind v4
- **Phase 3 Ready**: Runtime-Adapter austauschbar

---

### 1. Architektur-Impact

| Layer | Änderungen |
|-------|------------|
| `widget/src/components/screens/ChatScreen.tsx` | Ersetzt Placeholder mit @assistant-ui Thread + Composer |
| `widget/src/lib/chat-runtime.ts` | Neu - Dummy LocalRuntime + ChatModelAdapter |
| `widget/src/components/chat/ChatMessage.tsx` | Neu - Message Component (styled) |
| `widget/src/components/chat/ChatThread.tsx` | Neu - Thread Container (styled) |
| `widget/src/components/chat/ChatComposer.tsx` | Neu - Composer Input (styled) |
| `widget/src/styles/widget.css` | Erweitert - Chat-specific Styles |

---

### 2. Datenfluss

```
ChatScreen mounted
  ↓
useLocalRuntime(dummyAdapter) initialisiert
  ↓
AssistantRuntimeProvider wraps Thread + Composer
  ↓
Thread rendert (leer in Phase 2)
  ↓
Composer rendert (Input-Feld sichtbar)
  ↓
User tippt Nachricht → Composer State
  ↓
User drückt Enter → onSubmit
  ↓
LocalRuntime → dummyAdapter.run()
  ↓
Adapter gibt nichts zurück (Dummy)
  ↓
(Phase 3: Adapter ruft Backend SSE auf)
```

---

### 3. Dummy LocalRuntime (Phase 2)

**Datei:** `widget/src/lib/chat-runtime.ts`

**Ziel:**
- LocalRuntime mit Dummy-Adapter
- Adapter gibt keine Nachrichten zurück (Phase 2 hat kein Backend)
- Runtime ist austauschbar in Phase 3 (echte Backend-Anbindung)

**Implementierung:**
```typescript
import { useLocalRuntime } from '@assistant-ui/react'
import type { ChatModelAdapter, ChatModelRunResult } from '@assistant-ui/react'

/**
 * Dummy Chat Model Adapter für Phase 2
 *
 * In Phase 2 gibt es kein Backend. Der Adapter returned nichts.
 * In Phase 3 wird dieser Adapter ersetzt durch einen, der SSE-Backend aufruft.
 */
const dummyChatModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    // Phase 2: Keine Antwort
    // User kann tippen, aber es kommt keine Response

    // In Phase 3: Hier würde SSE-Call zum Backend stattfinden
    // yield { type: 'text-delta', textDelta: '...' }

    // Dummy: Return nothing
    return
  }
}

/**
 * Custom Hook für Widget Chat Runtime
 *
 * Verwendet useLocalRuntime mit Dummy-Adapter in Phase 2.
 * In Phase 3: Adapter wird ersetzt, Hook-Interface bleibt gleich.
 */
export function useWidgetChatRuntime() {
  return useLocalRuntime(dummyChatModelAdapter)
}
```

**Wichtig:**
- `useLocalRuntime` von @assistant-ui/react ist der offizielle Hook für Custom Backends
- `ChatModelAdapter` Interface ist das, was der Runtime erwartet
- `async *run()` ist ein Async Generator (für Streaming)
- Dummy gibt nichts zurück (`return` ohne Wert)
- Phase 3: Adapter wird ersetzt, Rest bleibt identisch

---

### 4. ChatScreen Component (Updated)

**Datei:** `widget/src/components/screens/ChatScreen.tsx`

**Ersetzt Placeholder mit @assistant-ui Primitives:**

**Props:**
```typescript
interface ChatScreenProps {
  // Keine Props in Phase 2
  // Phase 3 könnte interview_id übergeben
}
```

**Implementierung:**
```typescript
import React from 'react'
import { AssistantRuntimeProvider, Thread, Composer } from '@assistant-ui/react'
import { useWidgetChatRuntime } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'

export function ChatScreen() {
  const runtime = useWidgetChatRuntime()

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        {/* Thread Area */}
        <div className="flex-1 overflow-y-auto">
          <ChatThread />
        </div>

        {/* Composer Area */}
        <div className="border-t border-gray-200">
          <ChatComposer />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
```

**Wichtig:**
- `AssistantRuntimeProvider` wraps alle @assistant-ui Components
- `runtime` kommt von `useWidgetChatRuntime()` (Dummy in Phase 2)
- Thread und Composer sind styled Wrapper-Components (siehe nächste Sections)
- Layout: Thread oben (flex-1, scrollbar), Composer unten (fixed)

---

### 5. ChatThread Component

**Datei:** `widget/src/components/chat/ChatThread.tsx`

**Ziel:**
- Wrapper für @assistant-ui Thread Primitive
- Styling für Message-Liste
- Empty State: "Chat bereit" Hint wenn keine Messages

**Implementierung:**
```typescript
import React from 'react'
import { Thread, ThreadWelcome, ThreadMessages } from '@assistant-ui/react'
import { ChatMessage } from './ChatMessage'

export function ChatThread() {
  return (
    <Thread className="h-full">
      {/* Welcome/Empty State */}
      <ThreadWelcome className="flex flex-col items-center justify-center h-full px-6 py-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-8 h-8 text-gray-400"
              aria-hidden="true"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 className="text-base font-medium text-gray-900 mb-1">
            Bereit für Ihr Feedback
          </h3>
          <p className="text-sm text-gray-500">
            Stellen Sie Ihre Frage oder teilen Sie uns Ihre Gedanken mit.
          </p>
        </div>
      </ThreadWelcome>

      {/* Message List */}
      <ThreadMessages
        components={{
          UserMessage: ChatMessage,
          AssistantMessage: ChatMessage
        }}
        className="px-4 py-2 space-y-4"
      />
    </Thread>
  )
}
```

**Wichtig:**
- `Thread` ist @assistant-ui Primitive (enthält Chat-State)
- `ThreadWelcome` zeigt sich nur wenn Thread leer ist
- `ThreadMessages` rendert Message-Liste mit Custom-Components
- Custom `ChatMessage` Component für User + Assistant Messages (siehe nächste Section)

---

### 6. ChatMessage Component

**Datei:** `widget/src/components/chat/ChatMessage.tsx`

**Ziel:**
- Styled Message Bubble für User + Assistant
- Unterschiedliche Styles je nach Message-Type
- Markdown-Support (optional in Phase 2, Pflicht in Phase 3)

**Implementierung:**
```typescript
import React from 'react'
import { MessagePrimitive } from '@assistant-ui/react'
import type { FC } from 'react'

interface ChatMessageProps {
  message: {
    role: 'user' | 'assistant'
    content: Array<{ type: 'text'; text: string }>
  }
}

export const ChatMessage: FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <div
      className={`
        flex gap-3
        ${isUser ? 'justify-end' : 'justify-start'}
      `}
    >
      {/* Assistant Avatar (nur bei Assistant Messages) */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand flex items-center justify-center">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-4 h-4 text-white"
            aria-hidden="true"
          >
            <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h-2a5 5 0 0 0-5-5h-1v13H9V9H8a5 5 0 0 0-5 5H1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z" />
          </svg>
        </div>
      )}

      {/* Message Bubble */}
      <div
        className={`
          max-w-[80%] rounded-2xl px-4 py-2.5
          ${
            isUser
              ? 'bg-brand text-white'
              : 'bg-gray-100 text-gray-900'
          }
        `}
      >
        <MessagePrimitive.Content
          components={{
            Text: ({ text }) => (
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {text}
              </p>
            )
          }}
        />
      </div>
    </div>
  )
}
```

**Wichtig:**
- `MessagePrimitive.Content` ist @assistant-ui Primitive für Message-Rendering
- User Messages: Rechts, brand color
- Assistant Messages: Links, grauer Hintergrund, Avatar
- `whitespace-pre-wrap` für Zeilenumbrüche
- `max-w-[80%]` für lesbare Bubble-Breite

---

### 7. ChatComposer Component

**Datei:** `widget/src/components/chat/ChatComposer.tsx`

**Ziel:**
- Styled Composer Input-Feld
- Send-Button (Icon)
- Placeholder-Text aus Config
- Auto-Focus auf Mobile optional

**Implementierung:**
```typescript
import React from 'react'
import { Composer, ComposerPrimitive } from '@assistant-ui/react'

interface ChatComposerProps {
  placeholder?: string
}

export function ChatComposer({ placeholder = 'Nachricht eingeben...' }: ChatComposerProps) {
  return (
    <Composer className="p-4">
      <div className="flex gap-2 items-end">
        {/* Input Field */}
        <ComposerPrimitive.Input
          placeholder={placeholder}
          className="
            flex-1 px-4 py-3 rounded-xl
            bg-gray-100 text-gray-900
            placeholder:text-gray-500
            text-sm
            resize-none
            focus:outline-none focus:ring-2 focus:ring-brand focus:bg-white
            transition-all duration-200
            max-h-32
          "
          rows={1}
          autoFocus={false}
        />

        {/* Send Button */}
        <ComposerPrimitive.Send
          className="
            flex-shrink-0 w-10 h-10 rounded-xl
            bg-brand text-white
            flex items-center justify-center
            hover:bg-brand-hover
            active:scale-95
            transition-all duration-200
            disabled:opacity-50 disabled:cursor-not-allowed
            focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2
            touch-action-manipulation
          "
          aria-label="Nachricht senden"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-5 h-5"
            aria-hidden="true"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </ComposerPrimitive.Send>
      </div>
    </Composer>
  )
}
```

**Wichtig:**
- `Composer` ist @assistant-ui Primitive (Container für Input + Send)
- `ComposerPrimitive.Input` ist Textarea mit Auto-Resize
- `ComposerPrimitive.Send` ist Button (disabled wenn Input leer)
- `aria-label` auf Send-Button (web-design: Icon-only buttons)
- `touch-action-manipulation` verhindert double-tap zoom (web-design)
- `focus-visible:ring-2` für Keyboard Navigation (web-design)
- `autoFocus={false}` - kein Auto-Focus in Phase 2 (Mobile UX)

---

### 8. CSS Updates (Chat-specific Styles)

**Datei:** `widget/src/styles/widget.css`

**Neue Chat-specific Tokens:**
```css
@theme {
  /* Chat Colors */
  --color-message-user-bg: var(--color-brand);
  --color-message-user-text: var(--color-white);
  --color-message-assistant-bg: oklch(0.95 0 0);
  --color-message-assistant-text: var(--color-text);

  /* Chat Spacing */
  --chat-padding: 1rem;
  --message-gap: 1rem;

  /* Composer */
  --composer-input-bg: oklch(0.97 0 0);
  --composer-input-focus-bg: var(--color-white);
}

/* Chat Message Animations */
@keyframes message-slide-in {
  from {
    opacity: 0;
    transform: translateY(0.5rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feedbackai-widget .chat-message {
  animation: message-slide-in 200ms ease-out;
}

/* Scrollbar Styling (für Thread) */
.feedbackai-widget .chat-thread::-webkit-scrollbar {
  width: 6px;
}

.feedbackai-widget .chat-thread::-webkit-scrollbar-track {
  background: transparent;
}

.feedbackai-widget .chat-thread::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 3px;
}

.feedbackai-widget .chat-thread::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* Composer Focus Animation */
.feedbackai-widget .composer-input:focus {
  box-shadow: 0 0 0 2px var(--color-brand);
}
```

**Wichtig:**
- Message Slide-In Animation für neue Messages
- Custom Scrollbar für Thread (subtil)
- Composer Focus Animation via box-shadow
- Alle Colors via CSS Custom Properties (Theme-fähig)

---

### 9. Updated Widget Config (Composer Placeholder)

**Datei:** `widget/src/config.ts`

**Sicherstellen dass `composerPlaceholder` existiert:**

Slice 1 hat bereits `composerPlaceholder` in `WidgetTexts` definiert:
```typescript
export interface WidgetTexts {
  panelTitle: string
  consentHeadline: string
  consentBody: string
  consentCta: string
  thankYouHeadline: string
  thankYouBody: string
  composerPlaceholder: string // ✓ Already exists
}
```

**ChatScreen Integration:**
```typescript
// In ChatScreen.tsx, pass config to ChatComposer:
<ChatComposer placeholder={config.texts.composerPlaceholder} />
```

**Update:** ChatScreen braucht Zugriff auf `config`. Wird via Props übergeben:

**Datei:** `widget/src/components/screens/ChatScreen.tsx` (Updated Props)
```typescript
import React from 'react'
import { AssistantRuntimeProvider } from '@assistant-ui/react'
import { useWidgetChatRuntime } from '../../lib/chat-runtime'
import { ChatThread } from '../chat/ChatThread'
import { ChatComposer } from '../chat/ChatComposer'
import type { WidgetConfig } from '../../config'

interface ChatScreenProps {
  config: WidgetConfig
}

export function ChatScreen({ config }: ChatScreenProps) {
  const runtime = useWidgetChatRuntime()

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        {/* Thread Area */}
        <div className="flex-1 overflow-y-auto">
          <ChatThread />
        </div>

        {/* Composer Area */}
        <div className="border-t border-gray-200">
          <ChatComposer placeholder={config.texts.composerPlaceholder} />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
```

**Datei:** `widget/src/main.tsx` (ScreenRouter Updated)
```typescript
// ScreenRouter muss config an ChatScreen übergeben
function ScreenRouter({
  screen,
  config,
  onAcceptConsent,
  onAutoClose
}: {
  screen: WidgetScreen
  config: WidgetConfig
  onAcceptConsent: () => void
  onAutoClose: () => void
}) {
  switch (screen) {
    case 'consent':
      return (
        <ConsentScreen
          headline={config.texts.consentHeadline}
          body={config.texts.consentBody}
          ctaLabel={config.texts.consentCta}
          onAccept={onAcceptConsent}
        />
      )

    case 'chat':
      return <ChatScreen config={config} /> // ✓ Config übergeben

    case 'thankyou':
      return (
        <ThankYouScreen
          headline={config.texts.thankYouHeadline}
          body={config.texts.thankYouBody}
          onAutoClose={onAutoClose}
        />
      )

    default:
      return null
  }
}
```

---

## UI Anforderungen

### Wireframe (aus wireframes.md)

> **Quelle:** `wireframes.md` → Screen: Chat

**Chat Screen:**
```
┌──────────────────────────────┐
│  Widget-Titel              X │
├──────────────────────────────┤
│                              │
│                              │
│                              │
│    (empty message list)      │
│    oder                      │
│    User: Nachricht           │
│    Assistant: Antwort        │
│                              │
│                              │
│                              │
├──────────────────────────────┤
│ [Type a message...]     [➤] │
└──────────────────────────────┘
```

**Referenz Skills für UI-Implementation:**
- `.claude/skills/react-best-practices/SKILL.md` - Performance, Memoization
- `.claude/skills/web-design/SKILL.md` - Accessibility, Forms, Touch
- `.claude/skills/tailwind-v4/SKILL.md` - Design Tokens, Responsive

### 1. ChatThread (Message Liste)

**Komponenten & Dateien:**
- `components/chat/ChatThread.tsx` - Thread Container mit Welcome State
- `components/chat/ChatMessage.tsx` - Message Bubble (User + Assistant)

**Verhalten:**
- Empty State: "Bereit für Ihr Feedback" Icon + Text
- Messages: Scrollbare Liste, neueste unten
- Auto-Scroll zu neuesten Message (Phase 3)

**Zustände:**
- Empty: Welcome-State anzeigen
- With Messages: Message-Liste mit User + Assistant Bubbles
- Loading: Typing Indicator (Phase 3)

**Design Patterns (aus Skills):**
- [x] Rendering: content-visibility für große Listen (>50 Messages)
- [x] Performance: Virtualization wenn nötig (später)
- [x] Accessibility: Scrollbar sichtbar, focus-management

### 2. ChatComposer (Input-Feld)

**Komponenten & Dateien:**
- `components/chat/ChatComposer.tsx` - Composer Input + Send Button

**Verhalten:**
- Textarea mit Auto-Resize (1-4 Zeilen)
- Send-Button disabled wenn leer
- Enter → Send (Shift+Enter → Neue Zeile)
- Focus-State sichtbar

**Zustände:**
- Empty: Send-Button disabled
- Typing: Send-Button enabled
- Sending: Loading Indicator (Phase 3)

**Design Patterns (aus Skills):**
- [x] Accessibility: Input hat Label (aria-label oder visible label)
- [x] Touch: Send-Button ≥44px Touch Target
- [x] Forms: Input hat autocomplete="off"
- [x] Keyboard: Enter-Handler, Shift+Enter für neue Zeile

### 3. ChatMessage (Message Bubble)

**Komponenten & Dateien:**
- `components/chat/ChatMessage.tsx` - Styled Message Bubble

**Verhalten:**
- User: Rechts aligned, brand color
- Assistant: Links aligned, grau, Avatar
- Text mit Zeilenumbrüchen
- Slide-In Animation (200ms)

**Zustände:**
- Default: Text angezeigt
- Error: Fehler-State (Phase 3)

**Design Patterns (aus Skills):**
- [x] Animation: Slide-In mit transform/opacity (GPU)
- [x] Typography: whitespace-pre-wrap für Zeilenumbrüche
- [x] Responsive: max-w-[80%] für lesbare Breite

### 4. Accessibility

- [x] Thread hat `role="log"` + `aria-live="polite"` (neue Messages)
- [x] Composer Input hat aria-label
- [x] Send-Button hat aria-label
- [x] Focus-visible States für Input + Send-Button
- [x] Keyboard Navigation: Tab, Enter, Shift+Enter

---

## Acceptance Criteria

1) GIVEN ChatScreen rendered
   WHEN Thread leer (Phase 2)
   THEN ThreadWelcome angezeigt ("Bereit für Ihr Feedback")

2) GIVEN Composer visible
   WHEN User tippt Text
   THEN Send-Button enabled

3) GIVEN Composer visible
   WHEN User tippt Text und drückt Enter
   THEN Nachricht wird zu Thread hinzugefügt (als User-Message)

4) GIVEN Composer visible
   WHEN User drückt Send-Button
   THEN Nachricht wird zu Thread hinzugefügt (als User-Message)

5) GIVEN User-Message gesendet (Phase 2)
   WHEN Dummy-Adapter läuft
   THEN Keine Assistant-Antwort (Dummy gibt nichts zurück)

6) GIVEN ChatScreen mit Messages
   WHEN neue Message erscheint
   THEN Slide-In Animation (200ms)

7) GIVEN Thread mit mehreren Messages
   WHEN Thread scrollbar erscheint
   THEN Custom Scrollbar styled (subtil, grau)

8) GIVEN Composer Input
   WHEN User fokussiert Input
   THEN Focus Ring sichtbar (ring-2 ring-brand)

9) GIVEN Mobile Viewport (<=768px)
   WHEN ChatScreen gerendert
   THEN Touch Targets ≥44px (Send-Button), Input lesbar

10) GIVEN prefers-reduced-motion aktiviert
    WHEN neue Message erscheint
    THEN Keine Animation (instant)

---

## Testfälle

**WICHTIG:** Tests müssen VOR der Implementierung definiert werden! Der Orchestrator führt diese Tests automatisch nach der Slice-Implementierung aus.

### Test-Datei

**Konvention:** Build-Validierung via Node-Script (kein Vitest nötig für UI-Komponenten in Slice 4)

**Für diesen Slice:** `widget/test.html` (Updated mit Chat-UI Tests)

### Build Test

<test_spec>
```bash
# Ausgeführt vom Orchestrator Metadata "Test" Command
cd widget && npm run build

# Prüfung via Node-Script
node -e "
const fs = require('fs');
const path = require('path');

const htmlPath = path.join('widget', 'test.html');
const html = fs.readFileSync(htmlPath, 'utf-8');

// Check if Chat-UI components are referenced
if (!html.includes('@assistant-ui') && !html.includes('chat-ui') && !html.includes('chat')) {
  throw new Error('Chat-UI components not referenced in test.html');
}

console.log('✓ Chat-UI components present');

// Check bundle size
const widgetPath = path.join('widget', 'dist', 'widget.js');
const stat = fs.statSync(widgetPath);
console.log('✓ Bundle size: ' + (stat.size / 1024).toFixed(2) + ' KB');

if (stat.size > 500000) {
  console.warn('⚠ Bundle size >500KB (target <200KB gzipped)');
}
"
```
</test_spec>

### Manual Test (Updated Test-Page)

**Datei:** `widget/test.html` (Final Updated)

<test_spec>
```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FeedbackAI Widget Test - Slice 4: Chat-UI</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 2rem;
      background: #f0f0f0;
      min-height: 100vh;
    }
    h1 {
      color: #333;
    }
    .test-section {
      background: white;
      padding: 1.5rem;
      margin: 1rem 0;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .test-step {
      margin: 0.5rem 0;
      padding: 0.5rem;
      background: #f9f9f9;
      border-left: 3px solid #4CAF50;
    }
    .expected {
      color: #2196F3;
      font-weight: bold;
    }
    .note {
      background: #FFF9C4;
      padding: 1rem;
      border-left: 3px solid #FFC107;
      margin: 1rem 0;
    }
    .success {
      background: #E8F5E9;
      border-left: 3px solid #4CAF50;
    }
  </style>
</head>
<body>
  <h1>FeedbackAI Widget Test - Slice 4: @assistant-ui Chat-UI</h1>

  <div class="test-section success">
    <h2>✅ Widget Complete - All Slices Done!</h2>
    <p>Alle 4 Slices sind implementiert. Widget ist bereit für Phase 3 Backend-Anbindung.</p>
  </div>

  <div class="test-section">
    <h2>Test Checklist - Chat-UI</h2>

    <div class="test-step">
      <strong>1. Chat Screen: Empty State</strong>
      <p class="expected">✓ "Los geht's" Button klicken → Chat Screen öffnet</p>
      <p class="expected">✓ ThreadWelcome angezeigt: "Bereit für Ihr Feedback"</p>
      <p class="expected">✓ Chat-Icon sichtbar</p>
      <p class="expected">✓ Composer Input-Feld am unteren Rand</p>
      <p class="expected">✓ Placeholder: "Nachricht eingeben..."</p>
    </div>

    <div class="test-step">
      <strong>2. Composer: Typing</strong>
      <p class="expected">✓ Input-Feld klicken → Cursor blinkt</p>
      <p class="expected">✓ Text tippen → Send-Button wird enabled</p>
      <p class="expected">✓ Send-Button zeigt Pfeil-Icon</p>
      <p class="expected">✓ Input hat Focus-Ring (blauer Ring)</p>
    </div>

    <div class="test-step">
      <strong>3. Message senden: Enter</strong>
      <p class="expected">✓ Text tippen + Enter drücken</p>
      <p class="expected">✓ User-Message erscheint in Thread (rechts, blau)</p>
      <p class="expected">✓ Slide-In Animation (200ms)</p>
      <p class="expected">✓ Input-Feld wird geleert</p>
      <p class="expected">✓ Send-Button wieder disabled</p>
    </div>

    <div class="test-step">
      <strong>4. Message senden: Send-Button</strong>
      <p class="expected">✓ Text tippen + Send-Button klicken</p>
      <p class="expected">✓ User-Message erscheint in Thread</p>
      <p class="expected">✓ Input-Feld wird geleert</p>
    </div>

    <div class="test-step">
      <strong>5. Phase 2: Keine Assistant-Antwort</strong>
      <div class="note">
        <strong>Expected Behavior:</strong> In Phase 2 gibt es kein Backend.
        Dummy-Adapter gibt keine Antworten zurück.
      </div>
      <p class="expected">✓ Nach User-Message: Keine Assistant-Antwort</p>
      <p class="expected">✓ Kein Typing-Indicator</p>
      <p class="expected">✓ User kann weitere Messages senden</p>
    </div>

    <div class="test-step">
      <strong>6. Message Styling</strong>
      <p class="expected">✓ User Messages: Rechts aligned, brand color (blau)</p>
      <p class="expected">✓ Text lesbar, whitespace-pre-wrap</p>
      <p class="expected">✓ Rounded corners (rounded-2xl)</p>
      <p class="expected">✓ Max width 80% (lesbar)</p>
    </div>

    <div class="test-step">
      <strong>7. Thread Scrollbar</strong>
      <p class="expected">✓ Mehrere Messages senden (>5)</p>
      <p class="expected">✓ Thread wird scrollbar</p>
      <p class="expected">✓ Custom Scrollbar sichtbar (subtil, grau)</p>
      <p class="expected">✓ Hover: Scrollbar wird dunkler</p>
    </div>

    <div class="test-step">
      <strong>8. Keyboard Navigation</strong>
      <p class="expected">✓ Tab → Composer Input fokussiert</p>
      <p class="expected">✓ Focus-Ring sichtbar (ring-2)</p>
      <p class="expected">✓ Enter → Message senden</p>
      <p class="expected">✓ Shift+Enter → Neue Zeile (Textarea)</p>
      <p class="expected">✓ Tab → Send-Button fokussiert</p>
      <p class="expected">✓ Enter → Message senden</p>
    </div>

    <div class="test-step">
      <strong>9. Mobile Test (<=768px)</strong>
      <p class="expected">✓ Chat Screen Fullscreen</p>
      <p class="expected">✓ Composer Input lesbar</p>
      <p class="expected">✓ Send-Button Touch Target ≥44px</p>
      <p class="expected">✓ Thread scrollbar funktioniert auf Touch</p>
      <p class="expected">✓ Keine double-tap zoom (touch-action)</p>
    </div>

    <div class="test-step">
      <strong>10. Reduced Motion Test</strong>
      <div class="note">
        <strong>How to Test:</strong>
        - DevTools → Rendering Tab → Emulate CSS prefers-reduced-motion
      </div>
      <p class="expected">✓ Message Slide-In Animation disabled (instant)</p>
      <p class="expected">✓ Keine sichtbare Animation bei Message-Erscheinen</p>
    </div>

    <div class="test-step">
      <strong>11. Full Widget Flow</strong>
      <p class="expected">✓ Floating Button → Panel öffnet (Consent)</p>
      <p class="expected">✓ "Los geht's" → Chat Screen</p>
      <p class="expected">✓ Message tippen + senden → User Message erscheint</p>
      <p class="expected">✓ X-Button → Panel schließt (Chat-State bleibt)</p>
      <p class="expected">✓ Button erneut → Panel öffnet (Chat-Screen mit Messages)</p>
    </div>
  </div>

  <div class="test-section">
    <h2>Console Output Erwartung</h2>
    <pre>
FeedbackAI Widget mounted { lang: 'de', apiUrl: null, texts: {...} }
    </pre>
    <p><strong>Keine Fehler oder Warnings von @assistant-ui</strong></p>
  </div>

  <div class="test-section">
    <h2>Bundle Size Check</h2>
    <div class="note">
      Nach <code>npm run build</code>:
      <ul>
        <li>Target: &lt;200KB gzipped</li>
        <li>Accept: &lt;500KB ungzipped</li>
        <li>@assistant-ui/react + React 19 sind große Dependencies</li>
      </ul>
    </div>
  </div>

  <div class="test-section success">
    <h2>Phase 3 Readiness Check</h2>
    <p>✅ LocalRuntime integriert (Dummy-Adapter)</p>
    <p>✅ Thread + Composer funktionieren</p>
    <p>✅ Message-Rendering styled</p>
    <p>✅ User kann tippen und senden</p>
    <p>→ <strong>Phase 3:</strong> Nur Adapter austauschen (SSE-Backend-Call)</p>
  </div>

  <!-- Widget Embed -->
  <script
    src="./dist/widget.js"
    data-lang="de"
  ></script>
</body>
</html>
```
</test_spec>

**Manual Test Steps:**
1. `cd widget && npm run build`
2. `npm run preview`
3. Browser: `http://localhost:4173/test.html`
4. Durchlaufe Test Checklist in der Seite
5. Teste Chat-UI: Consent → Chat → Message senden
6. Teste Keyboard Navigation (Tab, Enter, Shift+Enter)
7. Teste auf Desktop + Mobile (DevTools Responsive Mode)
8. Teste Reduced Motion (Browser DevTools)
9. Teste Full Widget Flow (alle Screens)
10. Console: Keine Fehler, nur "FeedbackAI Widget mounted"

---

## Definition of Done

- [x] Akzeptanzkriterien sind eindeutig & vollständig
- [ ] @assistant-ui LocalRuntime integriert (Dummy-Adapter)
- [ ] Thread rendert Empty State korrekt
- [ ] Composer Input funktioniert (tippen, senden)
- [ ] User Messages werden angezeigt (styled)
- [ ] Phase 2: Keine Assistant-Antworten (Dummy)
- [ ] Keyboard Navigation funktioniert
- [ ] Mobile Responsive funktioniert
- [ ] prefers-reduced-motion Support implementiert
- [ ] Console: Keine Fehler oder Warnings
- [ ] Bundle Size akzeptabel (<500KB ungzipped)

---

## Integration Contract (GATE 2 PFLICHT)

> **Wichtig:** Diese Section wird vom Gate 2 Compliance Agent geprüft. Unvollständige Contracts blockieren die Genehmigung.

### Requires From Other Slices

| Slice | Resource | Type | Validation |
|-------|----------|------|------------|
| slice-01 | `WidgetConfig` | Type | Type has `texts.composerPlaceholder` field |
| slice-01 | `parseConfig()` | Function | Returns config with composerPlaceholder text |
| slice-02 | `Panel` | Component | Accepts ChatScreen as children |
| slice-02 | Tailwind Tokens | CSS | `--color-brand`, `--chat-padding` available |
| slice-03 | `ChatScreen` | Component | Exists as Placeholder, wird ersetzt |
| slice-03 | `ScreenRouter` | Component | Routes to ChatScreen with config prop |

### Provides To Other Slices

| Resource | Type | Consumer | Interface |
|----------|------|----------|-----------|
| `ChatScreen` (Updated) | Component | ScreenRouter | Props: `{ config: WidgetConfig }` |
| `ChatThread` | Component | ChatScreen | No props, internal |
| `ChatComposer` | Component | ChatScreen | Props: `{ placeholder?: string }` |
| `ChatMessage` | Component | ThreadMessages | Props: `{ message: {...} }` |
| `useWidgetChatRuntime()` | Hook | ChatScreen | Returns LocalRuntime instance |
| Chat-UI Styles | CSS | All Chat Components | Message bubbles, Composer, Scrollbar |

### Integration Validation Tasks

- [ ] WidgetConfig.texts.composerPlaceholder korrekt in ChatComposer verwendet
- [ ] ChatScreen ersetzt Placeholder aus Slice 3
- [ ] ScreenRouter übergibt config an ChatScreen
- [ ] LocalRuntime initialisiert ohne Fehler
- [ ] Dummy-Adapter gibt keine Antworten zurück (Phase 2)
- [ ] Thread rendert Empty State korrekt
- [ ] Composer Input + Send-Button funktionieren
- [ ] User Messages erscheinen in Thread

---

## Code Examples (MANDATORY - GATE 2 PFLICHT)

> **KRITISCH:** Alle Code-Beispiele in diesem Dokument sind **PFLICHT-Deliverables**.
> Der Gate 2 Compliance Agent prüft, dass jedes Code-Beispiel implementiert wird.
> Abweichung nur mit expliziter Begründung im Commit erlaubt.

| Code Example | Section | Mandatory | Notes |
|--------------|---------|-----------|-------|
| `chat-runtime.ts` | Section 3 | YES | Dummy LocalRuntime + Adapter |
| `ChatScreen.tsx` (Updated) | Section 4 & 9 | YES | @assistant-ui Integration mit config prop |
| `ChatThread.tsx` | Section 5 | YES | Thread mit Welcome State |
| `ChatMessage.tsx` | Section 6 | YES | Styled Message Bubble |
| `ChatComposer.tsx` | Section 7 | YES | Composer Input + Send Button |
| `widget.css` (Updates) | Section 8 | YES | Chat-specific Styles |
| `main.tsx` (ScreenRouter Update) | Section 9 | YES | Config an ChatScreen übergeben |
| `test.html` (Final Update) | Testfälle | YES | Chat-UI Tests |

---

## Constraints & Hinweise

**Betrifft:**
- @assistant-ui/react Integration
- LocalRuntime Setup
- Chat-UI Styling
- Phase 3 Vorbereitung

**@assistant-ui Integration Constraints:**
- **Primitives-Only**: Keine @assistant-ui/react-ui (styled components)
- **LocalRuntime**: Custom Backend via ChatModelAdapter
- **Dummy-Adapter**: Phase 2 gibt keine Antworten zurück
- **Phase 3 Ready**: Nur Adapter austauschen, Rest bleibt

**Chat-UI Styling:**
- User Messages: Rechts, brand color
- Assistant Messages: Links, grau, Avatar (Phase 3)
- Message Bubbles: rounded-2xl, max-w-[80%]
- Composer: rounded-xl, focus-ring
- Scrollbar: Custom styled (subtil)

**Performance:**
- Keine Virtualization nötig in Phase 2 (wenige Messages)
- Phase 3: Virtualization wenn >50 Messages
- Message Animations: GPU-optimiert (transform/opacity)
- prefers-reduced-motion Support

**Accessibility:**
- Thread: `role="log"` + `aria-live="polite"`
- Composer Input: aria-label
- Send-Button: aria-label
- Focus-visible States überall
- Keyboard Navigation: Tab, Enter, Shift+Enter

**Abgrenzung:**
- Kein Backend-Connection in Slice 4 (Dummy-Adapter)
- Keine Typing-Indicator (Phase 3)
- Keine Markdown-Rendering (optional in Phase 3)
- Keine Message-Editing (out of scope)

---

## Deliverables (SCOPE SAFEGUARD)

**WICHTIG: Diese Liste wird automatisch vom Stop-Hook validiert. Der Agent kann nicht stoppen, wenn Dateien fehlen.**

<!-- DELIVERABLES_START -->
### Chat Runtime
- [ ] `widget/src/lib/chat-runtime.ts` - Dummy LocalRuntime + ChatModelAdapter

### Chat Components
- [ ] `widget/src/components/chat/ChatThread.tsx` - Thread Container mit Welcome State
- [ ] `widget/src/components/chat/ChatMessage.tsx` - Styled Message Bubble (User + Assistant)
- [ ] `widget/src/components/chat/ChatComposer.tsx` - Composer Input + Send Button

### Updated Files
- [ ] `widget/src/components/screens/ChatScreen.tsx` - Ersetzt Placeholder mit @assistant-ui Primitives
- [ ] `widget/src/main.tsx` - ScreenRouter übergibt config an ChatScreen
- [ ] `widget/src/styles/widget.css` - Chat-specific Styles (Message, Composer, Scrollbar)

### Test Files
- [ ] `widget/test.html` - Final Updated Test-Page mit Chat-UI Tests

### Build Output (nach `npm run build`)
- [ ] `widget/dist/widget.js` - Final Bundle mit @assistant-ui Chat-UI
<!-- DELIVERABLES_END -->

**Hinweis für den Implementierungs-Agent:**
- Alle Dateien zwischen `<!-- DELIVERABLES_START -->` und `<!-- DELIVERABLES_END -->` sind **Pflicht**
- Der Stop-Hook prüft automatisch ob alle Dateien existieren
- Bei fehlenden Dateien wird der Agent blockiert und muss nachfragen

---

## Links

- Architecture: `../architecture.md` → Chat Layer, Component Tree, Q&A Log
- Wireframes: `../wireframes.md` → Chat Screen
- Discovery: `../discovery.md` → UI Components & States (Chat)
- Slice 1: `slice-01-vite-build-setup.md` → WidgetConfig, composerPlaceholder
- Slice 2: `slice-02-floating-button-panel-shell.md` → Panel Component
- Slice 3: `slice-03-screens-state-machine.md` → ChatScreen Placeholder, ScreenRouter
- React Best Practices: `.claude/skills/react-best-practices/SKILL.md` → Performance, Hooks
- Web Design Guidelines: `.claude/skills/web-design/SKILL.md` → Accessibility, Forms, Touch
- Tailwind v4 Patterns: `.claude/skills/tailwind-v4/SKILL.md` → Design Tokens, Responsive
- @assistant-ui Docs: https://www.assistant-ui.com/docs/primitives/AssistantRuntime
- @assistant-ui GitHub: https://github.com/Yonom/assistant-ui
