import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Login from "./Login";
import { api } from "../api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows the server's error when the password is wrong", async () => {
  // Fake the server's answer so no backend is needed
  vi.spyOn(api, "login").mockRejectedValue(new Error("Invalid username or password"));
  const onToast = vi.fn();
  render(<Login onLogin={vi.fn()} onToast={onToast} demoMode={false} />);

  await userEvent.type(screen.getByLabelText("Username"), "alice");
  await userEvent.type(screen.getByLabelText("Password"), "wrong");
  await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

  expect(onToast).toHaveBeenCalledWith("Invalid username or password", "error");
});
