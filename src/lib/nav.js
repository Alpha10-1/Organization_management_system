import {
  LayoutDashboard,
  Users,
  FolderLock,
  BarChart3,
  ShieldCheck,
} from "lucide-react";

export const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "staff"],
  },
  {
    label: "Clients",
    href: "/dashboard/clients",
    icon: Users,
    roles: ["admin", "staff"],
  },
  {
    label: "Files",
    href: "/dashboard/files",
    icon: FolderLock,
    roles: ["admin", "staff"],
  },
  {
    label: "Reports",
    href: "/dashboard/reports",
    icon: BarChart3,
    roles: ["admin", "staff"],
  },
  {
    label: "Users",
    href: "/dashboard/users",
    icon: ShieldCheck,
    roles: ["admin"],
  },
];