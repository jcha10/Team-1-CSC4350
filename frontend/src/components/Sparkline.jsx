import { useId } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

/**
 * Minimal inline trend chart - no axes/gridlines/tooltip, just a filled
 * line so a stat card can show "this is trending up" at a glance. Needs
 * at least 2 points to draw anything.
 */
export default function Sparkline({ data, color = "#1a1a1a", height = 28 }) {
  const gradientId = `spark-${useId()}`;
  const chartData = data.map((v, i) => ({ i, v }));

  if (chartData.length < 2) {
    return <div style={{ height }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradientId})`}
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
