"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { portalLogout } from "@/lib/portal-api";

export default function PortalShell({ user, children }) {
  const router = useRouter();

  async function handleLogout() {
    try {
      await portalLogout();
    } finally {
      router.replace("/portal/login");
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex flex-col gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-8">
        <Link href="/portal/home" className="flex items-center gap-2">
          <span className="rounded-xl bg-slate-900 px-3 py-1.5 text-sm font-bold text-white">
            OrgManage
          </span>
          <span className="text-sm font-medium text-slate-500">Client Portal</span>
        </Link>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-right">
            <p className="text-sm font-semibold text-slate-800">{user.name}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-6 lg:px-8">{children}</main>
    </div>
  );
}
