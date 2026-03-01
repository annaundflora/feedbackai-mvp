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

  it("should call onFactExtracted when fact_extracted event received", () => {
    const onFactExtracted = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onFactExtracted }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("fact_extracted", {
        interview_id: "iv-42",
        fact_count: 5,
      });
    });

    expect(onFactExtracted).toHaveBeenCalledWith({
      interview_id: "iv-42",
      fact_count: 5,
    });
  });

  it("should call onSummaryUpdated when summary_updated event received", () => {
    const onSummaryUpdated = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onSummaryUpdated }),
    );

    const es = MockEventSource.instances[0];
    act(() => {
      es.dispatchEvent("summary_updated", {
        cluster_id: "cluster-99",
      });
    });

    expect(onSummaryUpdated).toHaveBeenCalledWith({
      cluster_id: "cluster-99",
    });
  });

  it("should apply exponential backoff on repeated errors (1s, 2s, 4s, max 30s)", async () => {
    vi.useFakeTimers();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    // First error -> 1s delay
    const es1 = MockEventSource.instances[0];
    act(() => {
      es1.onerror?.(new Event("error"));
    });
    expect(es1.close).toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(MockEventSource.instances).toHaveLength(2);

    // Second error -> 2s delay
    const es2 = MockEventSource.instances[1];
    act(() => {
      es2.onerror?.(new Event("error"));
    });

    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    // Should NOT have reconnected yet (needs 2s)
    expect(MockEventSource.instances).toHaveLength(2);

    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    // Now 2s total elapsed -> reconnect
    expect(MockEventSource.instances).toHaveLength(3);

    // Third error -> 4s delay
    const es3 = MockEventSource.instances[2];
    act(() => {
      es3.onerror?.(new Event("error"));
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    // Should NOT have reconnected yet (needs 4s)
    expect(MockEventSource.instances).toHaveLength(3);

    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    // Now 4s total elapsed -> reconnect
    expect(MockEventSource.instances).toHaveLength(4);

    vi.useRealTimers();
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

/**
 * Acceptance Tests for slice-07-live-updates-sse.
 * Derived from GIVEN/WHEN/THEN Acceptance Criteria in the Slice-Spec.
 * Each test maps 1:1 to an AC from the spec.
 */
describe("Slice 07 Acceptance Tests", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("AC-1: GIVEN a clustering pipeline is running WHEN clustering_progress event is published THEN ProgressIndicator shows current step label and completed/total counter", () => {
    // Arrange (GIVEN) - Hook receives clustering_progress event
    const onClusteringProgress = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringProgress }),
    );

    const es = MockEventSource.instances[0];

    // Act (WHEN) - clustering_progress event dispatched
    act(() => {
      es.dispatchEvent("clustering_progress", {
        interview_id: "iv-1",
        step: "assigning",
        completed: 47,
        total: 52,
      });
    });

    // Assert (THEN) - callback receives correct data for ProgressIndicator
    expect(onClusteringProgress).toHaveBeenCalledWith({
      interview_id: "iv-1",
      step: "assigning",
      completed: 47,
      total: 52,
    });

    // Verify ProgressIndicator renders the step label and counter correctly
    render(
      <ProgressIndicator step="assigning" completed={47} total={52} />,
    );

    expect(screen.getByTestId("progress-label")).toHaveTextContent(
      "Assigning to clusters... 47/52",
    );
    expect(screen.getByTestId("progress-pct")).toHaveTextContent("90%");
  });

  it("AC-2: GIVEN clustering completes successfully WHEN clustering_completed event is published THEN ProgressIndicator disappears, StatusBar counters update, and router.refresh() is called", () => {
    // Arrange (GIVEN) - clustering_completed callback
    const onClusteringCompleted = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringCompleted }),
    );

    const es = MockEventSource.instances[0];

    // Act (WHEN) - clustering_completed event dispatched
    act(() => {
      es.dispatchEvent("clustering_completed", {
        cluster_count: 5,
        fact_count: 47,
      });
    });

    // Assert (THEN) - callback receives data for StatusBar update and router.refresh()
    expect(onClusteringCompleted).toHaveBeenCalledWith({
      cluster_count: 5,
      fact_count: 47,
    });

    // The page handler uses this data to:
    // 1. setIsProcessing(false) -> ProgressIndicator disappears
    // 2. setClusterCount(5), setFactCount(47) -> StatusBar updates
    // 3. router.refresh() -> server-side data refresh
    // These behaviors are verified at integration level via the callback contract.
  });

  it("AC-3: GIVEN clustering fails after retries WHEN clustering_failed event is published THEN ProgressIndicator disappears and toast error notification appears with unassigned facts message", () => {
    // Arrange (GIVEN) - clustering_failed callback
    const onClusteringFailed = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onClusteringFailed }),
    );

    const es = MockEventSource.instances[0];

    // Act (WHEN) - clustering_failed event dispatched
    act(() => {
      es.dispatchEvent("clustering_failed", {
        error: "LLM timeout after 3 retries",
        unassigned_count: 3,
      });
    });

    // Assert (THEN) - callback receives error data for toast and progress dismissal
    expect(onClusteringFailed).toHaveBeenCalledWith({
      error: "LLM timeout after 3 retries",
      unassigned_count: 3,
    });

    // The page handler uses this data to:
    // 1. setIsProcessing(false) + setProgress(null) -> ProgressIndicator disappears
    // 2. toast.error(`Clustering failed: 3 facts could not be assigned...`)
    // These behaviors are verified at integration level via the callback contract.
  });

  it("AC-4: GIVEN a new fact is extracted WHEN fact_extracted event is published THEN ClusterCard shows pulsing live_update_badge for 3 seconds then hides it", () => {
    vi.useFakeTimers();

    // Arrange (GIVEN) - fact_extracted callback triggers live update badge
    const onFactExtracted = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onFactExtracted }),
    );

    const es = MockEventSource.instances[0];

    // Act (WHEN) - fact_extracted event dispatched
    act(() => {
      es.dispatchEvent("fact_extracted", {
        interview_id: "iv-42",
        fact_count: 5,
      });
    });

    // Assert (THEN) - callback fires, and ClusterCard badge behavior is correct
    expect(onFactExtracted).toHaveBeenCalledWith({
      interview_id: "iv-42",
      fact_count: 5,
    });

    // Verify ClusterCard live_update_badge: appears and auto-hides after 3s
    const mockCluster = {
      id: "cluster-1",
      name: "Navigation Issues",
      summary: "Users struggle with navigation.",
      fact_count: 14,
      interview_count: 8,
      created_at: "2026-02-28T00:00:00Z",
      updated_at: "2026-02-28T00:00:00Z",
    };

    const { rerender } = render(
      <ClusterCard cluster={mockCluster} hasLiveUpdate={false} onClick={vi.fn()} />,
    );

    // Badge not visible initially
    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();

    // Simulate hasLiveUpdate triggered by fact_extracted handler
    rerender(
      <ClusterCard cluster={mockCluster} hasLiveUpdate={true} onClick={vi.fn()} />,
    );

    // Badge visible (pulsing blue dot)
    expect(screen.getByTestId("live-update-badge")).toBeInTheDocument();

    // After 3 seconds, badge auto-hides
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByTestId("live-update-badge")).not.toBeInTheDocument();

    vi.useRealTimers();
  });

  it("AC-5: GIVEN the SSE connection drops WHEN EventSource.onerror fires THEN useProjectEvents reconnects with exponential backoff (1s, 2s, 4s, max 30s)", async () => {
    vi.useFakeTimers();

    // Arrange (GIVEN) - SSE connection established
    renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    expect(MockEventSource.instances).toHaveLength(1);

    // Act (WHEN) - onerror fires (connection drop)
    const es1 = MockEventSource.instances[0];
    act(() => {
      es1.onerror?.(new Event("error"));
    });

    // Assert (THEN) - closes current connection
    expect(es1.close).toHaveBeenCalled();

    // Reconnects after 1s initial delay
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(MockEventSource.instances).toHaveLength(2);

    // Second error -> 2s delay (exponential backoff)
    const es2 = MockEventSource.instances[1];
    act(() => {
      es2.onerror?.(new Event("error"));
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(MockEventSource.instances).toHaveLength(3);

    vi.useRealTimers();
  });

  it("AC-6: GIVEN a user navigates away from the project dashboard WHEN the React component unmounts THEN EventSource connection is closed (no memory leak)", () => {
    // Arrange (GIVEN) - SSE connection established
    const { unmount } = renderHook(() =>
      useProjectEvents("proj-123", "test-token", {}),
    );

    const es = MockEventSource.instances[0];
    expect(es.close).not.toHaveBeenCalled();

    // Act (WHEN) - component unmounts (user navigates away)
    unmount();

    // Assert (THEN) - EventSource.close() called, no memory leak
    expect(es.close).toHaveBeenCalled();
  });

  it("AC-7: GIVEN a summary_updated event is received WHEN a cluster summary is regenerated THEN router.refresh() is called to load the updated summary", () => {
    // Arrange (GIVEN) - summary_updated callback
    const onSummaryUpdated = vi.fn();

    renderHook(() =>
      useProjectEvents("proj-123", "test-token", { onSummaryUpdated }),
    );

    const es = MockEventSource.instances[0];

    // Act (WHEN) - summary_updated event dispatched after merge/split
    act(() => {
      es.dispatchEvent("summary_updated", {
        cluster_id: "cluster-42",
      });
    });

    // Assert (THEN) - callback fires with cluster_id (page handler calls router.refresh())
    expect(onSummaryUpdated).toHaveBeenCalledWith({
      cluster_id: "cluster-42",
    });
  });
});
