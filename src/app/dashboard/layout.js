"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/layout/DashboardShell";
import { fetchCurrentUser } from "@/lib/api";

export default function DashboardLayout({ children }) {
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const currentUser = await fetchCurrentUser();
        setUser(currentUser);
      } catch (error) {
        setUser(null);
      } finally {
        setLoadingUser(false);
      }
    }

    loadUser();
  }, []);

  return (
    <ProtectedRoute>
      {loadingUser ? (
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-4 text-sm font-medium text-slate-600 shadow-sm">
            Loading dashboard...
          </div>
        </div>
      ) : user ? (
        <DashboardShell user={user}>{children}</DashboardShell>
      ) : null}
    </ProtectedRoute>
  );
}