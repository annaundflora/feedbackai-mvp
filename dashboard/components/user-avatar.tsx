// dashboard/components/user-avatar.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

interface UserAvatarProps {
  email: string;
}

function getInitials(email: string): string {
  return email.slice(0, 2).toUpperCase();
}

export function UserAvatar({ email }: UserAvatarProps): JSX.Element {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent): void {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout(): Promise<void> {
    setIsLoading(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen((o) => !o)}
        aria-label={`User menu for ${email}`}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 transition-colors touch-action-manipulation"
        data-testid="user-avatar-button"
      >
        {getInitials(email)}
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-40 rounded-lg border border-gray-200 bg-white shadow-md z-50"
          data-testid="user-menu"
        >
          <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-100 truncate">
            {email}
          </div>
          <button
            role="menuitem"
            onClick={handleLogout}
            disabled={isLoading}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:bg-gray-50 rounded-b-lg disabled:opacity-50 transition-colors"
            data-testid="logout-button"
          >
            {isLoading ? "Signing out…" : "Log out"}
          </button>
        </div>
      )}
    </div>
  );
}
