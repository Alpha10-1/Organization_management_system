"use client";

import { useRouter } from "next/navigation";
import { removeToken } from "@/lib/auth";

export default function AppHeader({ user }) {
  const router = useRouter();

  function handleLogout() {
    removeToken();
    router.replace("/login");
  }

  return (
    <header className="flex flex-col gap-4 border-b border-slate-200 bg-white px-5 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-8">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">
          Welcome back, {user.name.split(" ")[0]}
        </h2>
        <p className="text-sm text-slate-500">
          Manage clients, files, and reports from one place.
        </p>
      </div>

      <div className="flex items-center gap-3 self-start lg:self-auto">
        <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2">
          <div className="text-right">
            <p className="text-sm font-semibold text-slate-800">{user.name}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>
          <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
            {user.role}
          </span>
        </div>

        <button
          onClick={handleLogout}
          className="rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          Logout
        </button>
      </div>
    </header>
  );
}