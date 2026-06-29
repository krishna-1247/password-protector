"use client";

/**
 * useJobPoller.ts
 * ---------------
 * Polls GET /status/{jobId} every 1.5 seconds until the job reaches a
 * terminal state (completed | failed). Cleans up the interval automatically.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getStatus } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";

interface UseJobPollerResult {
  status: StatusResponse | null;
  isPolling: boolean;
  error: string | null;
  stopPolling: () => void;
}

const TERMINAL_STATES = new Set(["completed", "failed"]);
const POLL_INTERVAL_MS = 1500;

export function useJobPoller(jobId: string | null): UseJobPollerResult {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  useEffect(() => {
    if (!jobId) {
      stopPolling();
      setStatus(null);
      return;
    }

    setIsPolling(true);
    setError(null);

    const poll = async () => {
      try {
        const data = await getStatus(jobId);
        setStatus(data);
        if (TERMINAL_STATES.has(data.status)) {
          stopPolling();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Polling failed");
        stopPolling();
      }
    };

    // Immediate first poll
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => stopPolling();
  }, [jobId, stopPolling]);

  return { status, isPolling, error, stopPolling };
}
