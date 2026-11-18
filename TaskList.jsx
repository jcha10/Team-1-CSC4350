import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api";

/**
 * A private per-employee to-do list. Nobody else - not peers, not
 * hr_admin - has any route that can read another user's tasks (see
 * _owned_task() in main.py). Completing a task also increments the real
 * `tasks_completed` leaderboard metric server-side.
 */
export default function TaskList({ onToast }) {
  const [tasks, setTasks] = useState([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setTasks(await api.getTasks());
    } catch (err) {
      onToast(err.message || "Could not load tasks", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function addTask(e) {
    e.preventDefault();
    const title = draft.trim();
    if (!title) return;
    setDraft("");
    try {
      const task = await api.createTask(title);
      setTasks((prev) => [task, ...prev]);
    } catch (err) {
      onToast(err.message || "Could not add task", "error");
    }
  }

  async function toggle(task) {
    // Optimistic update - the UI shouldn't wait on a round trip to check a box.
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, is_done: !t.is_done } : t)));
    try {
      await api.updateTask(task.id, !task.is_done);
    } catch (err) {
      setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, is_done: task.is_done } : t)));
      onToast(err.message || "Could not update task", "error");
    }
  }

  async function remove(task) {
    setTasks((prev) => prev.filter((t) => t.id !== task.id));
    try {
      await api.deleteTask(task.id);
    } catch (err) {
      onToast(err.message || "Could not delete task", "error");
      load(); // resync on failure since the optimistic removal may be wrong
    }
  }

  const doneCount = tasks.filter((t) => t.is_done).length;

  return (
    <div className="bg-white border-4 border-black rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-extrabold text-black">✅ My Tasks</h2>
        {tasks.length > 0 && (
          <span className="text-xs text-gray-500">
            {doneCount}/{tasks.length} done
          </span>
        )}
      </div>

      <form onSubmit={addTask} className="flex gap-2 mb-3">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add a task…"
          aria-label="New task"
          maxLength={200}
          className="flex-1 border-2 border-black rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400"
        />
        <button
          type="submit"
          className="bg-black text-yellow-400 font-bold rounded-lg px-3 py-1.5 text-sm hover:bg-gray-800 transition"
        >
          Add
        </button>
      </form>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading…</p>
      ) : tasks.length === 0 ? (
        <p className="text-gray-500 text-sm">No tasks yet - add one above.</p>
      ) : (
        <ul className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
          <AnimatePresence initial={false}>
            {tasks.map((t) => (
              <motion.li
                key={t.id}
                layout
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-2 bg-yellow-50 rounded-lg px-3 py-1.5"
              >
                <input
                  type="checkbox"
                  checked={t.is_done}
                  onChange={() => toggle(t)}
                  aria-label={`Mark "${t.title}" ${t.is_done ? "not done" : "done"}`}
                  className="w-4 h-4 accent-black shrink-0"
                />
                <span
                  className={`flex-1 min-w-0 break-words text-sm ${
                    t.is_done ? "line-through text-gray-400" : "text-black"
                  }`}
                >
                  {t.title}
                </span>
                <button
                  onClick={() => remove(t)}
                  title="Delete task"
                  aria-label={`Delete "${t.title}"`}
                  className="text-gray-400 hover:text-red-600 text-xs shrink-0"
                >
                  ✕
                </button>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </div>
  );
}
