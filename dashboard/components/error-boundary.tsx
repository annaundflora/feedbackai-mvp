// dashboard/components/error-boundary.tsx
"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, errorMessage: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, errorMessage: error.message };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback !== undefined) {
        return this.props.fallback;
      }
      return (
        <div
          role="alert"
          className="flex flex-col items-center justify-center py-12 px-4 text-center"
          data-testid="error-boundary-fallback"
        >
          <span className="text-4xl mb-3" role="img" aria-hidden="true">⚠</span>
          <h3 className="text-base font-semibold text-gray-900 mb-1">
            Something went wrong
          </h3>
          <p className="text-sm text-gray-500 mb-4 max-w-xs">
            {this.state.errorMessage ?? "An unexpected error occurred. Please reload the page."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, errorMessage: null })}
            className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 focus-visible:ring-2 focus-visible:ring-gray-400 transition-colors"
            data-testid="error-boundary-retry"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
