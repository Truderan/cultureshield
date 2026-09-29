import { Link } from "react-router-dom";
import { BarChart3, BookOpen, CreditCard, FileText, LogOut, Settings, ShieldAlert, TrendingUp, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { key: "employees", label: "Employees", href: "/employees", icon: Users },
  { key: "analytics", label: "Analytics", href: "/analytics", icon: TrendingUp },
  { key: "reports", label: "Reports", href: "/reports", icon: FileText },
  { key: "board", label: "Board", href: "/standards-summary", icon: BookOpen },
  { key: "phishing", label: "Phishing", href: "/phishing", icon: ShieldAlert },
  { key: "billing", label: "Billing", href: "/billing", icon: CreditCard },
  { key: "security", label: "Security", href: "/settings/security", icon: Settings },
];

export const MobileAppNav = ({ current, onLogout }) => {
  return (
    <div className="mb-6 rounded-2xl border border-zinc-200 bg-white p-3  lg:hidden" data-testid="mobile-app-nav">
      <div className="flex flex-wrap gap-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.key === current;

          return (
            <Link key={item.key} to={item.href} data-testid={`mobile-nav-${item.key}`}>
              <Button
                variant={isActive ? "default" : "outline"}
                className={isActive ? "bg-[#18181B] text-white" : "border-zinc-300 text-[#18181B]"}
              >
                <Icon className="mr-2 h-4 w-4" />
                {item.label}
              </Button>
            </Link>
          );
        })}

        {onLogout && (
          <Button
            variant="ghost"
            className="text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={onLogout}
            data-testid="mobile-nav-logout"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        )}
      </div>
    </div>
  );
};