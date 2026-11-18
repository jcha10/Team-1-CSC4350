import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function DisloyaltyChart({ stats }) {
  const data = stats.map((s) => ({
    name: s.username,
    violations: s.violation_count,
    flagged: s.is_disloyal,
  }));

  return (
    <div className="bg-gray-900 border border-red-900/50 rounded-2xl p-5 shadow-lg">
      <h2 className="text-lg font-bold text-red-400 mb-4">Disloyalty Violations by Employee</h2>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
          <XAxis dataKey="name" stroke="#a1a1aa" fontSize={12} />
          <YAxis stroke="#a1a1aa" fontSize={12} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: "#ffffff10" }}
            contentStyle={{ background: "#18181b", border: "1px solid #7f1d1d", color: "#fca5a5" }}
            labelStyle={{ color: "#fca5a5" }}
            itemStyle={{ color: "#fca5a5" }}
          />
          <Bar dataKey="violations" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.flagged ? "#ef4444" : "#52525b"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
