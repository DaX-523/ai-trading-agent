import ModeToggle from "./ModeToggle";
import ThemeToggle from "./ThemeToggle";
import type { AppView, TradingMode } from "../lib/api";

type Props = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
  mode: TradingMode;
  onModeChange: (mode: TradingMode) => void;
  isDark: boolean;
  onToggleTheme: () => void;
};

const NAV_ITEMS: { id: AppView; label: string }[] = [
  { id: "dashboard", label: "DASHBOARD" },
  { id: "leaderboard", label: "LEADERBOARD" },
  { id: "models", label: "MODELS" },
];

export default function Navbar({
  activeView,
  onNavigate,
  mode,
  onModeChange,
  isDark,
  onToggleTheme,
}: Props) {
  return (
    <nav className="sticky top-0 z-50 border-b-2 border-black dark:border-white bg-white/90 dark:bg-gray-950/90 backdrop-blur">
      <div className="mx-auto max-w-[95vw] px-2">
        <div className="flex h-10 md:h-14 items-center justify-between font-bold">
          <div className="flex items-center">
            <button
              type="button"
              onClick={() => onNavigate("dashboard")}
              className="text-gray-900 dark:text-gray-100"
            >
              TRADUZE
            </button>
          </div>

          <div className="hidden items-end space-x-6 md:flex md:absolute md:left-1/2 md:-translate-x-1/2">
            {NAV_ITEMS.map((item, index) => (
              <span key={item.id} className="flex items-center space-x-6">
                {index > 0 && <span className="text-gray-900 dark:text-gray-100">|</span>}
                <button
                  type="button"
                  onClick={() => onNavigate(item.id)}
                  className={`font-mono text-sm transition-colors ${
                    activeView === item.id
                      ? "text-blue-600 dark:text-blue-400"
                      : "text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400"
                  }`}
                >
                  {item.label}
                </button>
              </span>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <ModeToggle mode={mode} onModeChange={onModeChange} />
            <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />
          </div>
        </div>
        <div className="flex md:hidden pb-2 gap-4">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`font-mono text-xs ${
                activeView === item.id
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-900 dark:text-gray-100"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  );
}
