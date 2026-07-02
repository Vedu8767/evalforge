"use client";
import { SessionProvider, useSession } from "next-auth/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useState, useEffect } from "react";

function QueryClientResetOnUserChange({ children, queryClient }: { children: React.ReactNode; queryClient: QueryClient }) {
  const { data: session } = useSession();
  const [lastUserId, setLastUserId] = useState<string | undefined>(undefined);

  useEffect(() => {
    const currentUserId = (session?.user as any)?.id || session?.user?.email;

    // If the logged-in user changed (different account), clear ALL cached
    // query data immediately. Without this, switching accounts can briefly
    // show the previous user's cached dashboard/eval-runs/models data
    // until each individual query happens to refetch on its own.
    if (lastUserId !== undefined && currentUserId !== lastUserId) {
      queryClient.clear();
    }
    setLastUserId(currentUserId);
  }, [session, lastUserId, queryClient]);

  return <>{children}</>;
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
    <SessionProvider>
      <QueryClientProvider client={queryClient}>
        <QueryClientResetOnUserChange queryClient={queryClient}>
          {children}
        </QueryClientResetOnUserChange>
        <Toaster theme="dark" position="top-right" />
      </QueryClientProvider>
    </SessionProvider>
  );
}
