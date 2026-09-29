import { ShieldCheck } from "lucide-react";

const SIZES = {
  sm: { icon: "h-4 w-4", text: "text-sm" },
  md: { icon: "h-5 w-5", text: "text-[15px]" },
  lg: { icon: "h-7 w-7", text: "text-xl" },
};

export const Brand = ({ size = "md", className = "" }) => {
  const s = SIZES[size] || SIZES.md;
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-tight text-foreground ${s.text} ${className}`}>
      <ShieldCheck className={s.icon} strokeWidth={1.75} />
      CultureShield
    </span>
  );
};

export default Brand;
