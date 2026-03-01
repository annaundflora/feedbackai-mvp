"use client";

import { useEffect, useRef, useCallback } from "react";

export type SseEventType =
  | "fact_extracted"
  | "clustering_started"
  | "clustering_progress"
  // clustering_updated intentionally omitted in Slice 7:
  // router.refresh() after clustering_completed fetches fresh cluster data server-side.
  // clustering_updated (granular card updates) is deferred to post-MVP optimization.
  | "clustering_completed"
  | "clustering_failed"
  | "summary_updated";

export interface FactExtractedData {
  interview_id: string;
  fact_count: number;
}

export interface ClusteringStartedData {
  mode: "incremental" | "full";
}

export interface ClusteringProgressData {
  interview_id: string;
  step: "extracting" | "assigning" | "validating" | "summarizing";
  completed: number;
  total: number;
}

export interface ClusteringCompletedData {
  cluster_count: number;
  fact_count: number;
}

export interface ClusteringFailedData {
  error: string;
  unassigned_count: number;
}

export interface SummaryUpdatedData {
  cluster_id: string;
}

export interface UseProjectEventsCallbacks {
  onFactExtracted?: (data: FactExtractedData) => void;
  onClusteringStarted?: (data: ClusteringStartedData) => void;
  onClusteringProgress?: (data: ClusteringProgressData) => void;
  onClusteringCompleted?: (data: ClusteringCompletedData) => void;
  onClusteringFailed?: (data: ClusteringFailedData) => void;
  onSummaryUpdated?: (data: SummaryUpdatedData) => void;
}

export function useProjectEvents(
  projectId: string,
  token: string,
  callbacks: UseProjectEventsCallbacks,
): void {
  // Store callbacks in ref to avoid re-connecting on every render (rerender-use-ref-transient-values)
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const reconnectDelayRef = useRef(1000);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
    }

    const url = `/api/projects/${projectId}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    const handleEvent = (eventType: SseEventType) => (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        const cb = callbacksRef.current;
        switch (eventType) {
          case "fact_extracted":
            cb.onFactExtracted?.(data as FactExtractedData);
            break;
          case "clustering_started":
            cb.onClusteringStarted?.(data as ClusteringStartedData);
            break;
          case "clustering_progress":
            cb.onClusteringProgress?.(data as ClusteringProgressData);
            break;
          case "clustering_completed":
            cb.onClusteringCompleted?.(data as ClusteringCompletedData);
            break;
          case "clustering_failed":
            cb.onClusteringFailed?.(data as ClusteringFailedData);
            break;
          case "summary_updated":
            cb.onSummaryUpdated?.(data as SummaryUpdatedData);
            break;
        }
        // Reset reconnect delay on successful message
        reconnectDelayRef.current = 1000;
      } catch {
        // Malformed JSON -- ignore, keep connection open
      }
    };

    const eventTypes: SseEventType[] = [
      "fact_extracted",
      "clustering_started",
      "clustering_progress",
      "clustering_completed",
      "clustering_failed",
      "summary_updated",
    ];
    eventTypes.forEach((type) => {
      es.addEventListener(type, handleEvent(type));
    });

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Exponential backoff: 1s, 2s, 4s, ... max 30s
      const delay = Math.min(reconnectDelayRef.current, 30_000);
      reconnectDelayRef.current = Math.min(delay * 2, 30_000);
      setTimeout(connect, delay);
    };
  }, [projectId, token]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [connect]);
}
