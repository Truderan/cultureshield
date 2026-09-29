import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BarChart3,
  BookOpen,
  CreditCard,
  FileText,
  LogOut,
  Menu,
  Settings,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/App";

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { key: "employees", label: "Employees", href: "/employees", icon: Users },
  { key: "analytics", label: "Analytics", href: "/analytics", icon: TrendingUp },
  { key: "reports", label: "Reports", href: "/reports", icon: FileText },
  { key: "phishing", label: "Phishing", href: "/phishing", icon: ShieldAlert },
  { key: "board", label: "Board summary", href: "/standards-summary", icon: BookOpen },
  { key: "billing", label: "Billing", href: "/billing", icon: CreditCard },
  { key: "security", label: "Security", href: "/settings/security", icon: Settings },
];

const Wordmark = () => (
  <Link to="/" className="flex items-center gap-2 text-foreground">
    <ShieldCheck className="h-5 w-5" strokeWidth={1.75} />
    <span className="text-[15px] font-semibold tracking-tight">CultureShield</span>
  </Link>
);

const NavList = ({ current, onNavigate }) => (
  <nav className="flex flex-col gap-0.5 px-3" aria-label="Main">
    {NAV_ITEMS.map(({ key, label, href, icon: Icon }) => {
      const active = key === current;
      return (
        <Link
          key={key}
          to={href}
          onClick={onNavigate}
          aria-current={active ? "page" : undefined}
          data-testid={`nav-${key}`}
          className={
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors " +
            (active
              ? "bg-muted font-medium text-foreground"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground")
          }
        >
          <Icon className="h-4 w-4" strokeWidth={1.75} />
          {label}
        </Link>
      );
    })}
  </nav>
);

const AccountBlock = ({ user, onLogout }) => (
  <div className="border-t p-4">
    <p className="truncate text-sm font-medium text-foreground">{user?.company_name}</p>
    <p className="mb-3 truncate text-xs text-muted-foreground">{user?.email}</p>
    <button
      type="button"
      onClick={onLogout}
      data-testid="logout-btn"
      className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <LogOut className="h-4 w-4" strokeWidth={1.75} />
      Log out
    </button>
  </div>
);

/**
 * One layout for every signed-in page.
 * - lg and up: fixed sidebar
 * - below lg: sticky top bar + slide-in menu
 */
export const AppShell = ({ current, children, testId, rootTestId }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background print:bg-white" data-testid={rootTestId}>
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r bg-background print:hidden lg:flex">
        <div className="px-6 py-6">
          <Wordmark />
        </div>
        <div className="flex-1 overflow-y-auto">
          <NavList current={current} />
        </div>
        <AccountBlock user={user} onLogout={handleLogout} />
      </aside>

      {/* Mobile / tablet top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background/90 px-4 backdrop-blur print:hidden lg:hidden">
        <Wordmark />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          data-testid="mobile-menu-btn"
          className="-mr-2 rounded-md p-2 text-foreground hover:bg-muted"
        >
          <Menu className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </header>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="flex w-72 flex-col p-0">
          <SheetTitle className="sr-only">Menu</SheetTitle>
          <SheetDescription className="sr-only">Navigate between sections</SheetDescription>
          <div className="px-6 py-6">
            <Wordmark />
          </div>
          <div className="flex-1 overflow-y-auto">
            <NavList current={current} onNavigate={() => setOpen(false)} />
          </div>
          <AccountBlock user={user} onLogout={handleLogout} />
        </SheetContent>
      </Sheet>

      <div className="lg:pl-60 print:pl-0">
        <main
          className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10 print:max-w-none print:p-0"
          data-testid={testId}
        >
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppShell;
