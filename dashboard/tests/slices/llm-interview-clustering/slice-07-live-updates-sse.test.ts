import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { useProjectEvents } from "@/hooks/useProjectEvents";
import { ProgressIndicator } from "@/components/progress-indicator";
import { ClusterCard } from "@/components/cluster-card";

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onerror: ((e: Event) => void) | null = null;
  private listeners: Map<string, ((e: MessageEvent) => void)[]> = new Map();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(handler);
  }

  dispatchEvent(type: string, data: object): void {
    const handlers = this.listeners.get(type) ?? [];
    const event = { data: JSON.stringify(data) } as MessageEvent;
    handlers.forEach((h) => h(event));
  }

  close = vi.fn();
}

describe("useProjectEvents", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should connect to SSE endpoint with correct URL", () => {
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/api/projects/proj-123/events");
    expect(MockEventSource.instances[0].url).toContain("token=test-token");

    unmount();
  });

  it("should call onClusteringProgress when clustering_progress event received", () => {
    const onClusteringProgress = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringProgress }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_progress", {
        interview_id: "iv-1",
        step: "assigning",
        completed: 3,
        total: 10,
      });
    });

    expect(onClusteringProgress).toHaveBeenCalledWith({
      interview_id: "iv-1",
      step: "assigning",
      completed: 3,
      total: 10,
    });
  });

  it("should call onClusteringCompleted when clustering_completed event received", () => {
    const onClusteringCompleted = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringCompleted }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_completed", {
        cluster_count: 5,
        fact_count: 47,
      });
    });

    expect(onClusteringCompleted).toHaveBeenCalledWith({
      cluster_count: 5,
      fact_count: 47,
    });
  });

  it("should call onClusteringFailed when clustering_failed event received", () => {
    const onClusteringFailed = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringFailed }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("clustering_failed", {
        error: "LLM timeout",
        unassigned_count: 3,
      });
    });

    expect(onClusteringFailed).toHaveBeenCalledWith({
      error: "LLM timeout",
      unassigned_count: 3,
    });
  });

  it("should reconnect with delay on onerror", async () => {
    vi.useFakeTimers();
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.onerror?.(new Event("error"));
    });

    expect(es.close).toHaveBeenCalled();

    // After 1s initial delay, reconnect
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances).toHaveLength(2);

    unmount();
    vi.useRealTimers();
  });

  it("should close EventSource on unmount", () => {
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    const es = MockEventSource.instances[0];
    unmount();

    expect(es.close).toHaveBeenCalled();
  });
});

describe("ProgressIndicator", () => {
  it("should render step label with completed/total counter", () => {
    render(
      <ProgressIndicator step="assigning" completed={3} total={10} />,
    );

    expect(screen.getByTestId("progress-label")).toHaveTextContent(
      "Assigning to clusters... 3/10",
    );
  });

  it("should show correct percentage", () => {
    render(
      <ProgressIndicator step="extracting" completed={5} total={10} />,
    );

    expect(screen.getByTestId("progress-pct")).toHaveTextContent("50%");
    const bar = screen.getByTestId("progress-bar-fill");
    expect(bar).toHaveStyle({ width: "50%" });
  });

  it("should have progressbar role with aria attributes", () => {
    render(
      <ProgressIndicator step="validating" completed={2} total={3} />,
    );

    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toHaveAttribute("aria-valuenow", "67");
    expect(progressbar).toHaveAttribute("aria-valuemin", "0");
    expect(progressbar).toHaveAttribute("aria-valuemax", "100");
  });

  it("should handle total=0 without division by zero", () => {
    render(
      <ProgressIndicator step="extracting" completed={0} total={0} />,
    );

    expect(screen.getByTestId("progress-pct")).toHaveTextContent("0%");
  });
});

describe("ClusterCard live_update_badge", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockCluster = {
    id: "cluster-1",
    name: "Navigation Issues",
    summary: "Users struggle with navigation.",
    fact_count: 14,
    interview_count: 8,
    created_at: "2026-02-28T00:00:00Z",
    updated_at: "2026-02-28T00:00:00Z",
  };

  it("should not show live_update_badge by default", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();
  });

  it("should show live_update_badge when hasLiveUpdate is true", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={true}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("live-update-badge")).toBeInTheDocument();
  });

  it("should hide live_update_badge after 3 seconds", () => {
    const { rerender } = render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    rerender(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={true}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("live-update-badge")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();
  });

  it("should display cluster name and fact count", () => {
    render(
      <ClusterCard
        cluster={mockCluster}
        hasLiveUpdate={false}
        onClick={vi.fn()}
      />,
    );

    expect(screen.getByTestId("cluster-card-name")).toHaveTextContent("Navigation Issues");
    expect(screen.getByTestId("cluster-fact-count")).toHaveTextContent("14 Facts");
  });

  it("should call onClick when Enter key pressed (keyboard accessibility)", () => {
    const onClick = vi.fn();
    render(
      <ClusterCard cluster={mockCluster} hasLiveUpdate={false} onClick={onClick} />,
    );

    const card = screen.getByTestId("cluster-card");
    card.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    expect(onClick).toHaveBeenCalled();
  });
});
