import { getModelColor } from "../lib/modelColor";

export type LeaderboardRow = {
  rank: number | null;
  modelId: string;
  name: string;
  currentValue: number | null;
  pnl: number | null;
  returnPct: number | null;
};

type Props = {
  data: LeaderboardRow[] | null;
  mode: string;
};

function formatMoney(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

export default function Leaderboard({ data, mode }: Props) {
  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400 font-medium animate-pulse">
        Loading leaderboard...
      </div>
    );
  }

  return (
    <div className="w-full h-full overflow-auto p-4 md:p-8">
      <div className="mb-4">
        <h2 className="text-sm font-bold text-black dark:text-white font-mono">LEADERBOARD</h2>
        <p className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1">
          Ranked by PnL vs $1,000 start · {mode}
        </p>
      </div>
      {data.length === 0 ? (
        <p className="font-mono text-sm text-gray-500 dark:text-gray-400">
          No models yet. Add one on the Models page.
        </p>
      ) : (
        <table className="w-full border-2 border-black dark:border-white font-mono text-sm">
          <thead className="bg-gray-100 dark:bg-gray-800">
            <tr>
              <th className="text-left p-2 border-b-2 border-black dark:border-white">RANK</th>
              <th className="text-left p-2 border-b-2 border-black dark:border-white">MODEL</th>
              <th className="text-right p-2 border-b-2 border-black dark:border-white">VALUE</th>
              <th className="text-right p-2 border-b-2 border-black dark:border-white">PNL</th>
              <th className="text-right p-2 border-b-2 border-black dark:border-white">RETURN</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => {
              const pnlClass =
                row.pnl === null
                  ? "text-gray-500 dark:text-gray-400"
                  : row.pnl >= 0
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-600 dark:text-red-400";
              return (
                <tr key={row.modelId} className="border-b border-gray-200 dark:border-gray-700">
                  <td className="p-2">{row.rank ?? "—"}</td>
                  <td className="p-2 font-semibold uppercase" style={{ color: getModelColor(row.name) }}>
                    {row.name}
                  </td>
                  <td className="p-2 text-right text-gray-900 dark:text-gray-100">{formatMoney(row.currentValue)}</td>
                  <td className={`p-2 text-right ${pnlClass}`}>{formatMoney(row.pnl)}</td>
                  <td className={`p-2 text-right ${pnlClass}`}>{formatPct(row.returnPct)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
