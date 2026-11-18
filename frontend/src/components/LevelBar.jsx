import { motion } from "framer-motion";

const LEVEL_TITLES = [
  "Newcomer",
  "Rising Star",
  "Team Player",
  "Star Performer",
  "Champion",
  "All-Star",
  "MVP",
  "Legend",
  "Icon",
  "Hall of Famer",
];
const POINTS_PER_LEVEL = 100;

export function levelForPoints(points) {
  const level = Math.floor(points / POINTS_PER_LEVEL) + 1;
  const progress = points % POINTS_PER_LEVEL;
  const title = LEVEL_TITLES[Math.min(level - 1, LEVEL_TITLES.length - 1)];
  return { level, progress, title };
}

export default function LevelBar({ points }) {
  const { level, progress, title } = levelForPoints(points);
  return (
    <div className="w-full max-w-xs">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-bold">
          Level {level} · {title}
        </span>
        <span className="opacity-70">
          {progress}/{POINTS_PER_LEVEL} to next
        </span>
      </div>
      <div className="h-2 rounded-full bg-yellow-400/20 overflow-hidden">
        <motion.div
          className="h-full bg-yellow-400"
          initial={false}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
