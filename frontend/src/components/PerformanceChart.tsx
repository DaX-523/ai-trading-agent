import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer, ReferenceLine } from "recharts";
import { getModelColor } from "../lib/modelColor";

type Props = { data: any[]; isDark: boolean };

export default function PerformanceChart({ data, isDark }: Props) {
  const { chartData, seriesNames } = useMemo(() => {
    if (!Array.isArray(data) || data.length === 0) {
      return { chartData: [], seriesNames: [] as string[] };
    }

    const points = data
      .map((item: any) => ({
        t: new Date(item.createdAt).getTime(),
        name: item.model?.name ?? item.modelId ?? "unknown",
        v: Number(item.netPortfolio),
      }))
      .filter((p) => Number.isFinite(p.v))
      .sort((a, b) => a.t - b.t);

    const names = new Set<string>();
    for (const p of points) names.add(p.name);

    const uniqueTs = Array.from(new Set(points.map((p) => p.t))).sort((a, b) => a - b);
    const gaps: number[] = [];
    for (let i = 1; i < uniqueTs.length; i++) gaps.push(uniqueTs[i] - uniqueTs[i - 1]);
    const medianGap = gaps.length ? gaps.sort((a, b) => a - b)[Math.floor(gaps.length / 2)] : 60_000;
    const tolerance = Math.min(5 * 60_000, Math.max(5_000, Math.floor((medianGap || 60_000) * 1.5)));

    const rows: any[] = [];
    let bucketStart = points[0].t;
    let bucketEnd = points[0].t;
    let bucketRows: Record<string, number> = {};

    const flush = () => {
      const center = Math.round((bucketStart + bucketEnd) / 2);
      rows.push({ t: center, ...bucketRows });
      bucketRows = {};
    };

    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      if (p.t - bucketEnd > tolerance) {
        flush();
        bucketStart = p.t;
        bucketEnd = p.t;
      }
      bucketEnd = Math.max(bucketEnd, p.t);
      bucketRows[p.name] = p.v;
    }
    flush();

    return { chartData: rows, seriesNames: Array.from(names.values()) };
  }, [data]);

  const axisFill = isDark ? "rgba(255, 255, 255, 0.8)" : "rgba(0, 0, 0, 0.8)";
  const axisStroke = isDark ? "rgba(255, 255, 255, 0.4)" : "rgba(0, 0, 0, 0.4)";
  const gridStroke = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)";
  const referenceStroke = isDark ? "rgba(255, 255, 255, 0.3)" : "rgba(0, 0, 0, 0.3)";

  return (
    <div className="relative w-full flex flex-1 border-r-2 border-black dark:border-white">
      <div className="absolute left-1/2 top-2 -translate-x-1/2 z-10">
        <h2 className="text-sm font-bold text-black dark:text-white font-mono">TOTAL ACCOUNT VALUE</h2>
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 40, right: 80, bottom: 0, left: 20 }}
        >
          <CartesianGrid
            strokeDasharray="1,3"
            stroke={gridStroke}
            strokeWidth={0.5}
          />

          <XAxis
            dataKey="t"
            type="number"
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => {
              const date = new Date(v);
              return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }}
            tick={{ fontSize: 12, fontFamily: 'monospace', fontWeight: 600, fill: axisFill }}
            stroke={axisStroke}
            strokeWidth={1.5}
          />

          <YAxis
            tick={{ fontSize: 12, fontFamily: 'Courier New, monospace', fontWeight: 600, fill: axisFill }}
            tickFormatter={(v: number) => `$${v.toLocaleString()}`}
            ticks={[500, 1000, 1500]}
            stroke={axisStroke}
            strokeWidth={1.5}
          />

          <Tooltip
            labelFormatter={(label: any) => new Date(label).toLocaleString()}
            contentStyle={{
              backgroundColor: isDark ? '#111827' : 'white',
              border: isDark ? '2px solid white' : '2px solid black',
              color: isDark ? '#f9fafb' : '#111827',
              fontFamily: 'monospace',
              fontSize: '12px'
            }}
          />

          <Legend
            wrapperStyle={{
              fontFamily: 'monospace',
              fontSize: '12px',
              color: axisFill,
            }}
          />

          <ReferenceLine
            y={1000}
            stroke={referenceStroke}
            strokeWidth={2}
            strokeDasharray="5 5"
          />

          {seriesNames.map((name) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              dot={false}
              strokeWidth={2}
              stroke={getModelColor(name)}
              strokeLinecap="round"
              strokeLinejoin="round"
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
