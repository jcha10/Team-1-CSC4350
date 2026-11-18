import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TaskList from "./TaskList";
import { api } from "../api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("typing a task and pressing Enter adds it to the list", async () => {
  // Fake the server: no tasks yet, and creating one echoes it back
  vi.spyOn(api, "getTasks").mockResolvedValue([]);
  vi.spyOn(api, "createTask").mockImplementation(async (title) => ({
    id: 1,
    title,
    is_done: false,
    created_at: "2026-10-30T12:00:00",
  }));
  render(<TaskList onToast={vi.fn()} />);

  await userEvent.type(screen.getByLabelText("New task"), "Ship sprint 4{Enter}");

  expect(api.createTask).toHaveBeenCalledWith("Ship sprint 4");
  expect(await screen.findByText("Ship sprint 4")).toBeTruthy();
});
