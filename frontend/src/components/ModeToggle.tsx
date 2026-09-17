import { useState, type FormEvent } from "react";
import { apiFetch, clearAdminToken, getAdminToken, setAdminToken, type TradingMode } from "../lib/api";

const MODES: TradingMode[] = ["SANDBOX", "TESTNET", "LIVE"];

type Props = {
  mode: TradingMode;
  onModeChange: (mode: TradingMode) => void;
};

export default function ModeToggle({ mode, onModeChange }: Props) {
  const [pendingMode, setPendingMode] = useState<TradingMode | null>(null);
  const [showTokenPrompt, setShowTokenPrompt] = useState(false);
  const [tokenInput, setTokenInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function commitMode(nextMode: TradingMode): Promise<void> {
    setSaving(true);
    setError(null);
    try {
      const response = await apiFetch("/settings/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: nextMode }),
      });
      if (response.status === 401) {
        clearAdminToken();
        setPendingMode(nextMode);
        setShowTokenPrompt(true);
        setError("Admin token required to change trading mode.");
        return;
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Failed to update trading mode");
      }
      const payload = await response.json();
      onModeChange(payload.mode as TradingMode);
      setPendingMode(null);
      setShowTokenPrompt(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update trading mode");
    } finally {
      setSaving(false);
    }
  }

  function requestMode(nextMode: TradingMode) {
    if (nextMode === mode || saving) {
      return;
    }
    if (nextMode === "LIVE") {
      setPendingMode("LIVE");
      setError(null);
      return;
    }
    if (!getAdminToken()) {
      setPendingMode(nextMode);
      setShowTokenPrompt(true);
      return;
    }
    void commitMode(nextMode);
  }

  function handleTokenSubmit(event: FormEvent) {
    event.preventDefault();
    const token = tokenInput.trim();
    if (!token) {
      setError("Enter the admin token.");
      return;
    }
    setAdminToken(token);
    setTokenInput("");
    setShowTokenPrompt(false);
    if (pendingMode) {
      void commitMode(pendingMode);
    }
  }

  return (
    <div className="relative flex items-center gap-2">
      <div className="flex border-2 border-black dark:border-white">
        {MODES.map((item) => {
          const active = item === mode;
          return (
            <button
              key={item}
              type="button"
              disabled={saving}
              onClick={() => requestMode(item)}
              className={`font-mono text-[10px] md:text-xs px-2 py-1 transition-colors ${
                active
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "bg-transparent text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              {item}
            </button>
          );
        })}
      </div>

      {pendingMode === "LIVE" && !showTokenPrompt && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 border-2 border-black dark:border-white bg-white dark:bg-gray-900 p-3 shadow-lg">
          <p className="font-mono text-xs text-gray-900 dark:text-gray-100 mb-3">
            Switch to LIVE trading? This will place real orders with real funds.
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="font-mono text-xs px-2 py-1 border-2 border-black dark:border-white"
              onClick={() => setPendingMode(null)}
            >
              CANCEL
            </button>
            <button
              type="button"
              className="font-mono text-xs px-2 py-1 bg-red-600 text-white border-2 border-red-600"
              onClick={() => {
                if (!getAdminToken()) {
                  setShowTokenPrompt(true);
                  return;
                }
                void commitMode("LIVE");
              }}
            >
              SWITCH TO LIVE
            </button>
          </div>
        </div>
      )}

      {showTokenPrompt && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 border-2 border-black dark:border-white bg-white dark:bg-gray-900 p-3 shadow-lg">
          <form onSubmit={handleTokenSubmit} className="flex flex-col gap-2">
            <label className="font-mono text-xs text-gray-900 dark:text-gray-100">
              Admin token
              <input
                type="password"
                value={tokenInput}
                onChange={(event) => setTokenInput(event.target.value)}
                className="mt-1 w-full border-2 border-black dark:border-white bg-transparent px-2 py-1 font-mono text-xs"
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="font-mono text-xs px-2 py-1 border-2 border-black dark:border-white"
                onClick={() => {
                  setShowTokenPrompt(false);
                  setPendingMode(null);
                }}
              >
                CANCEL
              </button>
              <button
                type="submit"
                className="font-mono text-xs px-2 py-1 bg-black text-white dark:bg-white dark:text-black border-2 border-black dark:border-white"
              >
                UNLOCK
              </button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <span className="hidden lg:inline font-mono text-[10px] text-red-600 dark:text-red-400 max-w-[180px]">
          {error}
        </span>
      )}
    </div>
  );
}
