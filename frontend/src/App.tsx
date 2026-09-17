import { useEffect, useState } from "react";
import PerformanceChart from "./components/PerformanceChart";
import RecentInvocations from "./components/RecentInvocations";
import Navbar from "./components/Navbar";
import Leaderboard, { type LeaderboardRow } from "./components/Leaderboard";
import ModelsManager from "./components/ModelsManager";
import { useDarkMode } from "./hooks/useDarkMode";
import { apiFetch, type AppView, type TradingMode } from "./lib/api";

function ChartSkeleton() {
  return (
    <div className="relative w-full flex flex-1 border-r-2 border-black dark:border-white">
      <div className="absolute left-1/2 top-2 -translate-x-1/2 z-10">
        <div className="h-4 w-48 rounded bg-gray-300 dark:bg-gray-700 animate-pulse" />
      </div>
      <div className="w-full h-full flex items-center justify-center p-8">
        <div className="w-full h-full rounded bg-linear-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 animate-pulse" />
      </div>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="hidden md:block md:w-[280px] lg:w-[320px] xl:w-[380px] 2xl:w-[500px] shrink-0 bg-surface md:overflow-hidden">
      <div className="flex h-full flex-col gap-4 overflow-y-auto p-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="px-2 py-2">
            <div className="flex space-x-2">
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <div className="h-4 w-24 rounded bg-gray-300 dark:bg-gray-700 animate-pulse" />
                  <div className="h-3 w-20 rounded bg-gray-200 dark:bg-gray-600 animate-pulse" />
                </div>
                <div className="rounded p-3 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                  <div className="space-y-2">
                    <div className="h-3 w-full rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
                    <div className="h-3 w-5/6 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
                    <div className="h-3 w-4/6 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [isDark, toggleDark] = useDarkMode();
  const [view, setView] = useState<AppView>("dashboard");
  const [mode, setMode] = useState<TradingMode>("SANDBOX");
  const [performanceData, setPerformanceData] = useState<any[] | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [invocationsData, setInvocationsData] = useState<any[] | null>(null);
  const [leaderboardData, setLeaderboardData] = useState<LeaderboardRow[] | null>(null);

  useEffect(() => {
    async function loadMode() {
      try {
        const response = await apiFetch("/settings/mode");
        if (!response.ok) {
          throw new Error("Failed to load trading mode");
        }
        const payload = await response.json();
        if (payload.mode) {
          setMode(payload.mode as TradingMode);
        }
      } catch (err) {
        console.error("Error fetching trading mode:", err);
      }
    }
    void loadMode();
  }, []);

  useEffect(() => {
    async function fetchData() {
      try {
        if (view === "dashboard") {
          const perfRes = await apiFetch(`/performance?mode=${mode}`);
          const perfData = await perfRes.json();
          setPerformanceData(perfData.data);
          setLastUpdated(perfData.lastUpdated);

          const invocRes = await apiFetch(`/invocations?limit=30&mode=${mode}`);
          const invocData = await invocRes.json();
          setInvocationsData(invocData.data);
          return;
        }
        if (view === "leaderboard") {
          const leaderboardRes = await apiFetch(`/leaderboard?mode=${mode}`);
          const leaderboardPayload = await leaderboardRes.json();
          setLeaderboardData(leaderboardPayload.data);
          setLastUpdated(leaderboardPayload.lastUpdated);
        }
      } catch (err) {
        console.error("Error fetching data:", err);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 3 * 60 * 1000);

    return () => clearInterval(interval);
  }, [mode, view]);

  const loading = !performanceData || !invocationsData;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-linear-to-b from-gray-50 to-gray-100 dark:from-gray-950 dark:to-gray-900 text-gray-900 dark:text-gray-100 font-[system-ui]">
      <Navbar
        activeView={view}
        onNavigate={setView}
        mode={mode}
        onModeChange={(nextMode) => {
          setMode(nextMode);
          setPerformanceData(null);
          setInvocationsData(null);
          setLeaderboardData(null);
        }}
        isDark={isDark}
        onToggleTheme={toggleDark}
      />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row overflow-y-auto md:overflow-hidden">
        {view === "dashboard" && (
          loading ? (
            <>
              <ChartSkeleton />
              <ListSkeleton />
            </>
          ) : (
            <>
              <PerformanceChart data={performanceData} isDark={isDark} />
              <RecentInvocations data={invocationsData} />
            </>
          )
        )}
        {view === "leaderboard" && (
          <Leaderboard data={leaderboardData} mode={mode} />
        )}
        {view === "models" && (
          <ModelsManager />
        )}
      </div>
      {lastUpdated && view !== "models" && (
        <div className="py-2 text-sm text-center text-gray-500 dark:text-gray-400 border-t-2 border-black dark:border-white">
          Last updated:{" "}
          <span className="font-medium text-gray-700 dark:text-gray-200">
            {new Date(lastUpdated).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      )}
    </div>
  );
}
