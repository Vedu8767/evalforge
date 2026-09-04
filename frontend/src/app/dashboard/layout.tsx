"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { useEffect } from "react";
import {
  LayoutDashboard, Database, Play, Cpu,
  Settings, Shield, Zap, LogOut, User
} from "lucide-react";
import { clsx } from "clsx";
import { ThemeToggle } from "../theme-toggle";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/eval-runs", label: "Eval Runs", icon: Play },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/models", label: "Models", icon: Cpu },
  { href: "/red-team", label: "Red Team", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-gray-500 text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  if (!session) return null;

  const handleSignOut = async () => {
    // redirect: false + manual router.push, rather than signOut's own
    // callbackUrl redirect. Letting NextAuth do a full-page redirect at the
    // same moment the "unauthenticated" useEffect above fires router.push
    // created a navigation race that could leave the session cookie half
    // -cleared in production, which is what broke logging back in.
    await signOut({ redirect: false });
    router.push("/login");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col">

        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Zap size={15} className="text-white" />
            </div>
            <span className="font-semibold text-white tracking-tight">EvalForge</span>
          </div>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "bg-indigo-600/20 text-indigo-300"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User info + Logout */}
        <div className="px-3 py-4 border-t border-gray-200 dark:border-gray-800 space-y-1">
          {/* User info */}
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800/50">
            <div className="w-6 h-6 bg-indigo-600/30 rounded-full flex items-center justify-center flex-shrink-0">
              <User size={12} className="text-indigo-400" />
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">
                {session.user?.name || "User"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-600 truncate">
                {session.user?.email || ""}
              </div>
            </div>
          </div>

          {/* Theme toggle */}
          <ThemeToggle />

          {/* Logout button */}
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:text-red-400 hover:bg-red-900/10 transition-colors"
          >
            <LogOut size={16} />
            Sign out
          </button>

          <div className="text-xs text-gray-400 dark:text-gray-700 px-3 pt-1">EvalForge v0.1</div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
