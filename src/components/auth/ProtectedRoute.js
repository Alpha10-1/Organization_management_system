"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchCurrentUser } from "@/lib/api";

export default function ProtectedRoute({ children }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    async function checkAuth() {
      try {
        await fetchCurrentUser();
        setAuthorized(true);
      } catch (error) {
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }

    checkAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-2xl border border-slate-200 bg-white px-6 py-4 text-sm font-medium text-slate-600 shadow-sm">
          Loading...
        </div>
      </div>
    );
  }

  if (!authorized) return null;

  return children;
}