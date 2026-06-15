import { ModeToggle } from "@/components/mode-toggle";
import { ThemeProvider } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";

/** 脚手架占位首页：演示 ThemeProvider + shadcn Button + 暗色切换，删掉换成你的页面即可。 */
export default function App() {
  return (
    <ThemeProvider>
      <div className="flex min-h-svh flex-col items-center justify-center gap-6 p-8">
        <h1 className="font-bold text-3xl">React + Vite + Tailwind + shadcn</h1>
        <p className="text-muted-foreground">脚手架已就绪，开始构建你的界面。</p>
        <div className="flex items-center gap-3">
          <Button>主按钮</Button>
          <Button variant="outline">次按钮</Button>
          <ModeToggle />
        </div>
      </div>
    </ThemeProvider>
  );
}
