import {
  QueryClient,
  QueryClientProvider,
  focusManager,
  onlineManager,
} from "@tanstack/react-query";
import * as Network from "expo-network";
import { useEffect } from "react";
import { AppState, Platform, type AppStateStatus } from "react-native";

import { ApiError, ApiTransportError } from "@rest/api-client";

/**
 * One client for the whole app.
 *
 * Retries are deliberately narrow: a 4xx is a decision the server already made
 * (forbidden, already accepted, idempotency conflict) and retrying it just
 * delays the truth. Transport failures are retried once, because a dropped
 * Wi-Fi packet on the floor is common and the request is idempotent by design.
 */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError) {
    return error.status >= 500 && failureCount < 2;
  }
  if (error instanceof ApiTransportError) {
    return failureCount < 1;
  }
  return false;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Staff screens poll; this keeps a freshly mounted screen from flashing a
      // spinner when it already has data from a moment ago.
      staleTime: 5_000,
      gcTime: 5 * 60_000,
      retry: shouldRetry,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      // Never silently replay a mutation: order and payment writes carry an
      // Idempotency-Key, but the operator should still see the failure.
      retry: false,
    },
  },
});

/**
 * The app must show authoritative state after the device comes back to the
 * foreground or the network returns. TanStack Query does this through
 * `focusManager` and `onlineManager`; both need a React Native adapter.
 */
function useNativeQueryAdapters(): void {
  useEffect(() => {
    if (Platform.OS === "web") return;

    const onChange = (status: AppStateStatus) => {
      focusManager.setFocused(status === "active");
    };
    const subscription = AppState.addEventListener("change", onChange);
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (Platform.OS === "web") return;

    const subscription = Network.addNetworkStateListener((state) => {
      onlineManager.setOnline(
        Boolean(state.isConnected) && state.isInternetReachable !== false
      );
    });
    void Network.getNetworkStateAsync()
      .then((state) =>
        onlineManager.setOnline(
          Boolean(state.isConnected) && state.isInternetReachable !== false
        )
      )
      .catch(() => {
        // Unknown reachability: assume online and let the request fail loudly.
      });

    return () => subscription.remove();
  }, []);
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  useNativeQueryAdapters();
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
