import { useState } from "react";
import { Download, Smartphone } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";

export const InstallAppButton = ({
  className = "",
  variant = "outline",
  size = "default",
  testId = "install-app-button",
}) => {
  const { canInstall, isInstalled, installApp } = useInstallPrompt();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (isInstalled) {
      toast.success("CultureShield is already installed on this device.");
      return;
    }

    if (!canInstall) {
      toast.info("Use your browser's install or add-to-home-screen option to download the app.");
      return;
    }

    setLoading(true);
    const result = await installApp();
    setLoading(false);

    if (result.status === "accepted") {
      toast.success("CultureShield download started.");
    } else if (result.status === "dismissed") {
      toast.info("Install prompt dismissed.");
    }
  };

  return (
    <Button variant={variant} size={size} className={className} onClick={handleClick} data-testid={testId}>
      {isInstalled ? <Smartphone className="mr-2 h-4 w-4" /> : <Download className="mr-2 h-4 w-4" />}
      {loading ? "Preparing..." : isInstalled ? "Installed" : "Download App"}
    </Button>
  );
};