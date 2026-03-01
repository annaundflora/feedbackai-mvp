"use client";

/**
 * Minimal Toast-System fuer Fehler-Benachrichtigungen.
 *
 * Verwendet ein einfaches Event-System (CustomEvent) statt einer externen Bibliothek.
 * Toasts erscheinen oben rechts und auto-dismissieren sich.
 *
 * Slice 7: Wird fuer clustering_failed Events verwendet.
 */

import { useState, useEffect, useCallback, useRef } from "react";

interface ToastMessage {
  id: string;
  type: "error" | "success" | "info";
  message: string;
  duration: number;
}

// Event-Name fuer imperatives toast() API
const TOAST_EVENT = "feedbackai:toast";

// Imperatives API fuer toast.error(), toast.success() etc.
export const toast = {
  error: (message: string, duration = 8000) => {
    const event = new CustomEvent(TOAST_EVENT, {
      detail: { type: "error", message, duration },
    });
    if (typeof window !== "undefined") {
      window.dispatchEvent(event);
    }
  },
  success: (message: string, duration = 4000) => {
    const event = new CustomEvent(TOAST_EVENT, {
      detail: { type: "success", message, duration },
    });
    if (typeof window !== "undefined") {
      window.dispatchEvent(event);
    }
  },
  info: (message: string, duration = 4000) => {
    const event = new CustomEvent(TOAST_EVENT, {
      detail: { type: "info", message, duration },
    });
    if (typeof window !== "undefined") {
      window.dispatchEvent(event);
    }
  },
};

function ToastItem({
  toast: t,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(t.id), t.duration);
    return () => clearTimeout(timer);
  }, [t.id, t.duration, onDismiss]);

  const bgClass =
    t.type === "error"
      ? "bg-red-600"
      : t.type === "success"
        ? "bg-green-600"
        : "bg-gray-800";

  return (
    <div
      role={t.type === "error" ? "alert" : "status"}
      aria-live={t.type === "error" ? "assertive" : "polite"}
      data-testid={`toast-${t.type}`}
      className={`${bgClass} text-white px-4 py-3 rounded-lg shadow-lg max-w-sm flex items-start gap-3`}
    >
      <p className="flex-1 text-sm">{t.message}</p>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss(t.id)}
        className="text-white/80 hover:text-white text-lg leading-none flex-shrink-0"
      >
        ×
      </button>
    </div>
  );
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const counterRef = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handler = (e: CustomEvent<{ type: "error" | "success" | "info"; message: string; duration: number }>) => {
      const id = `toast-${++counterRef.current}`;
      setToasts((prev) => [
        ...prev,
        { id, ...e.detail },
      ]);
    };

    window.addEventListener(TOAST_EVENT as string, handler as EventListener);
    return () => {
      window.removeEventListener(TOAST_EVENT as string, handler as EventListener);
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Notifications"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
      ))}
    </div>
  );
}
