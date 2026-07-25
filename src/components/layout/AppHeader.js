"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Search, X } from "lucide-react";
import {
  logoutUser,
  globalSearch,
  fetchNotifications,
  fetchUnreadNotificationCount,
  markNotificationRead,
  markAllNotificationsRead,
  requestEmailVerification,
} from "@/lib/api";

const SEARCH_GROUP_LABELS = {
  clients: "Clients",
  files: "Files",
  tasks: "Tasks",
  users: "Users",
};

export default function AppHeader({ user }) {
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchBoxRef = useRef(null);

  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const notifBoxRef = useRef(null);

  const [verifyDismissed, setVerifyDismissed] = useState(false);
  const [verifySending, setVerifySending] = useState(false);
  const [verifySent, setVerifySent] = useState(false);

  async function handleLogout() {
    try {
      await logoutUser();
    } finally {
      router.replace("/login");
    }
  }

  // Debounced global search
  useEffect(() => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    const timeout = setTimeout(async () => {
      try {
        const results = await globalSearch(query.trim());
        setSearchResults(results);
        setSearchOpen(true);
      } catch {
        setSearchResults(null);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  // Poll unread notification count
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const { count } = await fetchUnreadNotificationCount();
        if (!cancelled) setUnreadCount(count);
      } catch {
        // ignore transient failures
      }
    }
    poll();
    const interval = setInterval(poll, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(event) {
      if (searchBoxRef.current && !searchBoxRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
      if (notifBoxRef.current && !notifBoxRef.current.contains(event.target)) {
        setNotifOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function openNotifications() {
    setNotifOpen((open) => !open);
    if (!notifOpen) {
      try {
        const list = await fetchNotifications();
        setNotifications(list);
      } catch {
        setNotifications([]);
      }
    }
  }

  async function handleNotificationClick(notification) {
    if (!notification.is_read) {
      try {
        await markNotificationRead(notification.id);
        setUnreadCount((count) => Math.max(0, count - 1));
        setNotifications((list) =>
          list.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n))
        );
      } catch {
        // non-fatal
      }
    }
    setNotifOpen(false);
    if (notification.link) router.push(notification.link);
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications((list) => list.map((n) => ({ ...n, is_read: true })));
    } catch {
      // non-fatal
    }
  }

  async function handleResendVerification() {
    try {
      setVerifySending(true);
      await requestEmailVerification();
      setVerifySent(true);
    } catch {
      // non-fatal; user can retry
    } finally {
      setVerifySending(false);
    }
  }

  function goToResult(link) {
    setSearchOpen(false);
    setQuery("");
    setSearchResults(null);
    router.push(link);
  }

  const hasResults =
    searchResults &&
    Object.values(searchResults).some((group) => Array.isArray(group) && group.length > 0);

  return (
    <>
      {!user.is_verified && !verifyDismissed ? (
        <div className="flex flex-col items-start justify-between gap-2 border-b border-amber-200 bg-amber-50 px-5 py-2.5 text-sm text-amber-800 sm:flex-row sm:items-center lg:px-8">
          <span>
            {verifySent
              ? "Verification email sent — check your inbox."
              : "Your email address hasn't been verified yet."}
          </span>
          <div className="flex items-center gap-3">
            {!verifySent && (
              <button
                onClick={handleResendVerification}
                disabled={verifySending}
                className="font-semibold underline hover:text-amber-900 disabled:opacity-60"
              >
                {verifySending ? "Sending..." : "Resend verification email"}
              </button>
            )}
            <button
              onClick={() => setVerifyDismissed(true)}
              className="text-amber-600 hover:text-amber-900"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : null}

      <header className="flex flex-col gap-4 border-b border-slate-200 bg-white px-5 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-8">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">
          Welcome back, {user.name.split(" ")[0]}
        </h2>
        <p className="text-sm text-slate-500">
          Manage clients, files, and reports from one place.
        </p>
      </div>

      <div className="flex flex-1 items-center justify-end gap-3 self-start lg:self-auto">
        <div ref={searchBoxRef} className="relative w-full max-w-xs">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => query.trim() && setSearchOpen(true)}
              placeholder="Search clients, files, tasks..."
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-8 text-sm text-slate-800 outline-none transition focus:border-slate-400 focus:bg-white"
            />
            {query && (
              <button
                onClick={() => {
                  setQuery("");
                  setSearchResults(null);
                }}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-slate-400 hover:bg-slate-200"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {searchOpen && query.trim() && (
            <div className="absolute right-0 z-20 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg">
              {!searchResults && (
                <p className="px-3 py-2 text-sm text-slate-400">Searching...</p>
              )}
              {searchResults && !hasResults && (
                <p className="px-3 py-2 text-sm text-slate-400">No results for &ldquo;{query}&rdquo;</p>
              )}
              {searchResults &&
                Object.entries(searchResults).map(([group, items]) =>
                  items && items.length > 0 ? (
                    <div key={group} className="mb-1 last:mb-0">
                      <p className="px-3 pt-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                        {SEARCH_GROUP_LABELS[group] || group}
                      </p>
                      {items.map((item) => (
                        <button
                          key={`${group}-${item.id}`}
                          onClick={() => goToResult(item.link)}
                          className="flex w-full flex-col items-start rounded-xl px-3 py-2 text-left text-sm hover:bg-slate-50"
                        >
                          <span className="font-medium text-slate-800">{item.label}</span>
                          {item.subtitle && (
                            <span className="text-xs text-slate-500">{item.subtitle}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  ) : null
                )}
            </div>
          )}
        </div>

        <div ref={notifBoxRef} className="relative">
          <button
            onClick={openNotifications}
            className="relative rounded-2xl border border-slate-200 bg-slate-50 p-2.5 text-slate-600 transition hover:bg-slate-100"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 z-20 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-2 shadow-lg">
              <div className="flex items-center justify-between px-3 pb-1 pt-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Notifications
                </p>
                {notifications.some((n) => !n.is_read) && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-xs font-semibold text-slate-500 hover:text-slate-800"
                  >
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.length === 0 && (
                  <p className="px-3 py-4 text-sm text-slate-400">You&rsquo;re all caught up.</p>
                )}
                {notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`flex w-full flex-col items-start rounded-xl px-3 py-2 text-left text-sm transition hover:bg-slate-50 ${
                      n.is_read ? "opacity-60" : ""
                    }`}
                  >
                    <span className="font-medium text-slate-800">{n.title}</span>
                    {n.body && <span className="text-xs text-slate-500">{n.body}</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

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
    </>
  );
}
