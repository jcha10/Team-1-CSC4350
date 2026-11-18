import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Header from "./Header";
import { api } from "../api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// Draws the header for a user and fakes the server's "am I hr_admin?" answer.
function renderHeader(role, serverSaysHrAdmin) {
  vi.spyOn(api, "verifyHrAccess").mockResolvedValue(serverSaysHrAdmin);
  const setMode = vi.fn();
  render(
    <Header mode="smile" setMode={setMode} user={{ username: "alice", role }} onLogout={vi.fn()} onToast={vi.fn()} />
  );
  return setMode;
}

async function tripleClickLogo() {
  const logo = screen.getByRole("button", { name: "Smiley" });
  for (let i = 0; i < 3; i++) await userEvent.click(logo);
}

it("does not switch modes when an employee triple-clicks the logo", async () => {
  const setMode = renderHeader("employee", false);
  await tripleClickLogo();

  await waitFor(() => expect(api.verifyHrAccess).toHaveBeenCalledOnce());
  expect(setMode).not.toHaveBeenCalled();
});

it("switches to Predatory Mode when hr_admin triple-clicks the logo", async () => {
  const setMode = renderHeader("hr_admin", true);
  await tripleClickLogo();

  await waitFor(() => expect(setMode).toHaveBeenCalledWith("predatory"));
});
