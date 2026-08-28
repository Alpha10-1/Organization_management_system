"use client";

import { useEffect, useState } from "react";
import PortalProtectedRoute from "@/components/portal/PortalProtectedRoute";
import PortalShell from "@/components/portal/PortalShell";
import { fetchPortalCurrentUser } from "@/lib/portal-api";

export default function PortalHomeLayout({ children }) {
  const [user, setUser] = useState(null);
  const [loadingUser, setLoadingUser] = useState(true);

  useEffect(() => {
    async function loadUser() {
      try {
        const currentUser = await fetchPortalCurrentUser();
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
    <PortalProtectedRoute>
      {loadingUser ? (
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <div className="rounded-2xl border border-slate-200 bg-white px-6 py-4 text-sm font-medium text-slate-600 shadow-sm">
            Loading portal...
          </div>
        </div>
      ) : user ? (
        <PortalShell user={user}>{children}</PortalShell>
      ) : null}
    </PortalProtectedRoute>
  );
}
