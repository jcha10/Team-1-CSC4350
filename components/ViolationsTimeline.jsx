import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * Violation count per minute, bucketed client-side from the same activity
 * feed events already loaded for the live feed - no separate backend
 * aggregation endpoint needed.
 */
export default function ViolationsTimeline({ events }) {
  const buckets = {};
  events.forEach((e) => {
    if (!e.is_flagged) return;
    const d = new Date(e.timestamp);
    const key = `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
    buckets[key] = (buckets[key] || 0) + 1;
  });
  const data = Object.entries(buckets).map(([time, violations]) => ({ time, violations }));

  return (
    <div className="bg-gray-900 border border-red-900/50 rounded-2xl p-5 shadow-lg">
      <h2 className="text-lg font-bold text-red-400 mb-4">Violations Over Time</h2>
      {data.length === 0 ? (
        <p className="text-gray-500 text-sm">No violations recorded yet.</p>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
            <XAxis dataKey="time" stroke="#a1a1aa" fontSize={11} />
            <YAxis stroke="#a1a1aa" fontSize={11} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #7f1d1d", color: "#fca5a5" }}
              labelStyle={{ color: "#fca5a5" }}
              itemStyle={{ color: "#fca5a5" }}
            />
            <Line
              type="monotone"
              dataKey="violations"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ r: 3, fill: "#ef4444" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
