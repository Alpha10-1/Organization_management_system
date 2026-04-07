import AppHeader from "./AppHeader";
import AppSidebar from "./AppSidebar";

export default function DashboardShell({ user, children }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <AppSidebar role={user.role} />

      <div className="flex min-h-screen flex-1 flex-col">
        <AppHeader user={user} />
        <main className="flex-1 px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}