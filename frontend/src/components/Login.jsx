import { useState } from "react";
import { api } from "../api";


/**
 * Login component for user authentication. This component renders a login form and handles the submission of user credentials. It also displays a demo mode message if the application is running in demo mode.
 */
export default function Login({ onLogin, onToast, demoMode }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  /**
   * Handle form submission for user login. This function prevents the default form submission behavior, checks if both username and password are provided, and then attempts to log in the user using the API. If successful, it calls the onLogin callback with the received token and user details. If an error occurs, it displays a toast message with the error.
   */
  async function submit(e) {
    e.preventDefault();
    if (!username || !password) return;
    setBusy(true);
    try {
      const { token, user } = await api.login(username.trim(), password);
      onLogin(token, user);
    } catch (err) {
      onToast(err.message || "Login failed", "error");
    } finally {
      setBusy(false);
    }
  }

  /**
   * Render the login form with input fields for username and password, a submit button, and a demo mode message if applicable. The form is styled with Tailwind CSS classes for a responsive and visually appealing layout.
   * The input fields are controlled components, with their values managed by the component's state. The submit button is disabled while the login request is in progress or if either input field is empty.
   * The demo mode message provides information about the demo credentials for testing purposes.
   */
  return (
    <div className="min-h-screen bg-yellow-400 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm border-4 border-black">
        <div className="text-center mb-6">
          <div className="text-6xl mb-2" aria-hidden="true">
            😊
          </div>
          <h1 className="text-2xl font-extrabold text-black">Smiley</h1>
          <p className="text-sm text-gray-600">Employee Engagement Platform</p>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <input
            className="w-full border-2 border-black rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
            placeholder="Username"
            aria-label="Username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <input
            className="w-full border-2 border-black rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-500"
            placeholder="Password"
            aria-label="Password"
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="submit"
            disabled={busy || !username || !password}
            className="w-full bg-black text-yellow-400 font-bold rounded-lg py-2 hover:bg-gray-800 transition disabled:opacity-50"
          >
            {busy ? "Signing in…" : "Sign In"}
          </button>
        </form>
        {demoMode && (
          <div className="mt-4 text-xs text-gray-500 text-center leading-relaxed">
            Demo mode — password <code>password123</code> for all accounts:
            <br />
            employees: alice, bob, carol, dave &middot; admin: hr_admin
          </div>
        )}
      </div>
    </div>
  );
}
