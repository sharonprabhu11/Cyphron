"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { mutate } from "swr";

import { getBackendBaseUrl } from "@/lib/api";
import { DASHBOARD_SWR_KEYS } from "@/lib/dashboardSwrKeys";

type RealtimeCtx = {
  connected: boolean;
  /** When true, SWR can use longer refreshInterval; Firestore listeners are active on the server. */
  reducePolling: boolean;
};

const DashboardRealtimeContext = createContext<RealtimeCtx>({
  connected: false,
  reducePolling: false,
});

function debounce<T extends (...args: unknown[]) => void>(fn: T, ms: number) {
  let id: number | undefined;
  return (...args: Parameters<T>) => {
    if (id !== undefined) window.clearTimeout(id);
    id = window.setTimeout(() => fn(...args), ms);
  };
}

export function DashboardRealtimeProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [socketPushesEnabled, setSocketPushesEnabled] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const reconnectTimerRef = useRef<number | undefined>(undefined);

  const revalidateDashboard = useMemo(
    () =>
      debounce(() => {
        for (const key of DASHBOARD_SWR_KEYS) {
          void mutate(key);
        }
      }, 450),
    []
  );

  useEffect(() => {
    const httpBase = getBackendBaseUrl();
    if (!httpBase) {
      return undefined;
    }

    const wsBase =
      (typeof window !== "undefined" && process.env.NEXT_PUBLIC_WS_URL?.trim()) ||
      httpBase.replace(/^http/, "ws");
    const url = `${wsBase.replace(/\/$/, "")}/ws/dashboard`;

    const clearReconnect = () => {
      if (reconnectTimerRef.current !== undefined) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = undefined;
      }
    };

    const connect = () => {
      clearReconnect();
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          backoffRef.current = 1000;
        };

        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data as string) as { kind?: string; realtime?: boolean };
            if (msg.kind === "hello" && msg.realtime === false) {
              setSocketPushesEnabled(false);
              return;
            }
            if (msg.kind === "hello") {
              setSocketPushesEnabled(true);
              return;
            }
            if (msg.kind === "refresh") {
              setSocketPushesEnabled(true);
              revalidateDashboard();
            }
          } catch {
            /* ignore non-JSON */
          }
        };

        ws.onclose = () => {
          setConnected(false);
          wsRef.current = null;
          reconnectTimerRef.current = window.setTimeout(() => {
            backoffRef.current = Math.min(backoffRef.current * 2, 60_000);
            connect();
          }, backoffRef.current);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        setConnected(false);
        reconnectTimerRef.current = window.setTimeout(connect, backoffRef.current);
      }
    };

    connect();

    return () => {
      clearReconnect();
      wsRef.current?.close();
      wsRef.current = null;
      setConnected(false);
    };
  }, [revalidateDashboard]);

  const reducePolling = connected && socketPushesEnabled;

  const value = useMemo(
    () => ({ connected, reducePolling }),
    [connected, reducePolling]
  );

  return (
    <DashboardRealtimeContext.Provider value={value}>{children}</DashboardRealtimeContext.Provider>
  );
}

export function useDashboardRealtime() {
  return useContext(DashboardRealtimeContext);
}

/** @alias useDashboardRealtime */
export const useDashboardSocket = useDashboardRealtime;
