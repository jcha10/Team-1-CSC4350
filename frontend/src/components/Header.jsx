/**
 * Top bar: the app name, who is signed in (and their role), and Log out.
 */

/**
 * Header component that displays the application name, the currently signed-in user's username and role, and a logout button. The component receives the `user` object and an `onLogout` callback function as props. The header is styled with Tailwind CSS classes for a sticky top bar with a yellow background and black text.
 * The user's role is displayed as "HR Admin" for users with the "hr_admin" role, and "Employee" for all other users. The logout button triggers the `onLogout` callback when clicked, allowing the parent component to handle the logout process.
 */
export default function Header({ user, onLogout }) {
  return (
    /**
     * Render the header with the application name, user information, and logout button. The header is styled to be sticky at the top of the page, with a yellow background and black text. The user's username and role are displayed on the right side, along with a logout button that calls the `onLogout` function when clicked.
     */
    <header className="sticky top-0 z-40 flex items-center justify-between px-6 py-3 border-b-4 bg-yellow-400 border-black text-black">
      <div className="flex items-center gap-2 font-extrabold text-lg select-none">
        <span className="text-2xl">😊</span>
        <span>Smiley</span>
      </div>

      {/* Display the signed-in user's username and role. */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-black/70">
          {user.username} · {user.role === "hr_admin" ? "HR Admin" : "Employee"}
        </span>
        <button
          onClick={onLogout}
          className="font-semibold rounded-lg px-3 py-1 border-2 border-black text-black hover:bg-black hover:text-yellow-400 transition"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
