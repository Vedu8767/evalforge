"use client";
import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950 p-8">
      <div className="max-w-md w-full bg-gray-900 rounded-2xl border border-gray-800 p-8 text-center">
        <div className="w-12 h-12 bg-red-900/30 rounded-xl flex items-center justify-center mx-auto mb-4">
          <AlertTriangle size={24} className="text-red-400" />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">Something went wrong</h2>
        <p className="text-gray-500 text-sm mb-6">
          {error.message || "An unexpected error occurred. Please try again."}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Try again
          </button>
          <button
            onClick={() => window.location.href = "/dashboard"}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
        {error.digest && (
          <p className="text-xs text-gray-700 mt-4">Error ID: {error.digest}</p>
        )}
      </div>
    </div>
  );
}
