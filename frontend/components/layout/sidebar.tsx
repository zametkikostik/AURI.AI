"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Calendar,
  Search,
  Settings,
  Shield,
  Mic2,
  LogIn,
  LogOut,
  Users,
  CreditCard,
  BookOpen,
} from "lucide-react";
import { useI18n } from "@/lib/i18n/context";
import { LanguageSwitcher } from "@/components/layout/language-switcher";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();

  const nav = [
    { href: "/", label: t.nav.dashboard, icon: LayoutDashboard },
    { href: "/meetings", label: t.nav.meetings, icon: Calendar },
    { href: "/search", label: t.nav.search, icon: Search },
    { href: "/knowledge", label: t.nav.knowledge, icon: BookOpen },
    { href: "/team", label: t.nav.team, icon: Users },
    { href: "/billing", label: t.nav.billing, icon: CreditCard },
    { href: "/settings", label: t.nav.settings, icon: Settings },
  ];

  function logout() {
    localStorage.removeItem("auri_access_token");
    localStorage.removeItem("auri_refresh_token");
    router.push("/login");
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r bg-card">
      <div className="flex items-center gap-2 border-b px-4 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Mic2 className="h-5 w-5" />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight">{t.appName}</div>
          <div className="text-[10px] text-muted-foreground">strict_private</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 p-3">
        {nav.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="space-y-3 border-t p-3">
        <LanguageSwitcher />
        <div className="flex items-center gap-2 px-1 text-[10px] text-muted-foreground">
          <Shield className="h-3 w-3" />
          <span className="leading-tight">{t.footer.privacy}</span>
        </div>
        <div className="flex gap-2">
          <Link
            href="/login"
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md border px-2 py-1.5 text-xs hover:bg-secondary"
          >
            <LogIn className="h-3.5 w-3.5" />
            {t.nav.login}
          </Link>
          <button
            type="button"
            onClick={logout}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-md border px-2 py-1.5 text-xs hover:bg-secondary"
          >
            <LogOut className="h-3.5 w-3.5" />
            {t.nav.logout}
          </button>
        </div>
      </div>
    </aside>
  );
}
