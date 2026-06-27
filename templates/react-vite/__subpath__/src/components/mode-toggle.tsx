import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

/** 主题切换按钮：深色显月、浅色显日，点击在 dark/light 间切换（基于实际生效主题 resolvedTheme）。 */
export function ModeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      title="切换主题"
    >
      <Sun className="h-[1.2rem] w-[1.2rem] scale-100 transition-all dark:scale-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 transition-all dark:scale-100" />
      <span className="sr-only">切换主题</span>
    </Button>
  );
}
