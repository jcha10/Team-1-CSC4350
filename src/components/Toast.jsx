import { AnimatePresence, motion } from "framer-motion";

/**
 * Toast notifications. These are always honest about what actually
 * happened on the backend - e.g. toggling a visibility switch says
 * "removed from the public APM leaderboard", never anything implying
 * monitoring itself has stopped.
 */
export default function ToastStack({ toasts }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className={`rounded-lg shadow-lg px-4 py-3 text-sm font-medium border ${
              t.type === "error"
                ? "bg-red-50 text-red-800 border-red-300"
                : "bg-white text-gray-900 border-gray-200"
            }`}
          >
            {t.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
