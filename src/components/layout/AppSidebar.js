"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "@/lib/nav";

export default function AppSidebar({ role }) {
  const pathname = usePathname();

  const filteredItems = navItems.filter((item) => item.roles.includes(role));

  return (
    <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
      <div className="border-b border-slate-200 px-6 py-5">
        <h1 className="text-lg font-bold tracking-tight text-slate-900">
          OrgManage
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Management System
        </p>
      </div>

      <nav className="flex-1 px-4 py-4">
        <div className="space-y-2">
          {filteredItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition ${
                  active
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </aside>
  );
}