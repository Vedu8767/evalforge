"use client";
import { SessionProvider, useSession } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useEffect, useRef, useState } from "react";
import { ThemeProvider, useTheme } from "./theme-provider";

function QueryClientResetOnUserChange({ children, queryClient }: { children: React.ReactNode; queryClient: QueryClient }) {
  const { data: session, status } = useSession();
  // Refs (not state) so we always compare against the true previous value,
  // even across the intermediate "logged out" render that happens between
  // two different accounts logging in one after another.
  const lastUserIdRef = useRef<string | null>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Don't act on the transient "loading" status — wait for a settled
    // authenticated/unauthenticated state so we don't clear on every
    // background session re-check.
    if (status === "loading") return;

    const currentUserId =
      status === "authenticated"
        ? (session?.user as any)?.id ?? session?.user?.email ?? null
        : null;

    if (!initializedRef.current) {
      // First settled render after page load — just record it, nothing to
      // clear yet.
      lastUserIdRef.current = currentUserId;
      initializedRef.current = true;
      return;
    }

    // Fires for EVERY transition: user A -> logout (null) -> user B, not
    // just a direct A -> B switch. This is the case the old undefined-check
    // logic missed, which is exactly why a second account kept seeing the
    // first account's cached dashboard/eval-runs/chart data.
    if (currentUserId !== lastUserIdRef.current) {
      queryClient.clear();
      lastUserIdRef.current = currentUserId;
    }
  }, [session, status, queryClient]);

  return <>{children}</>;
}

function ThemedToaster() {
  const { theme } = useTheme();
  return <Toaster theme={theme} position="top-right" />;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 0,
            refetchOnMount: "always",
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  return (
    <ThemeProvider>
      <SessionProvider>
        <QueryClientProvider client={queryClient}>
          <QueryClientResetOnUserChange queryClient={queryClient}>
            {children}
          </QueryClientResetOnUserChange>
          <ThemedToaster />
        </QueryClientProvider>
      </SessionProvider>
    </ThemeProvider>
  );
}
