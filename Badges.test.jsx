import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import Badges from "./Badges";

afterEach(cleanup);

// A user with every stat at zero except points.
const userWith = (points) => ({
  points,
  apm: 0,
  total_clicks: 0,
  active_screen_time: 0,
  current_streak: 0,
  kudos_received: 0,
});

it("fires the Century Club message once when points pass 100, not again after", () => {
  const onUnlock = vi.fn();
  const { rerender } = render(<Badges user={userWith(50)} onUnlock={onUnlock} />);
  expect(onUnlock).not.toHaveBeenCalled();

  rerender(<Badges user={userWith(150)} onUnlock={onUnlock} />);
  expect(onUnlock).toHaveBeenCalledTimes(1);
  expect(onUnlock.mock.calls[0][0].label).toBe("Century Club");

  rerender(<Badges user={userWith(160)} onUnlock={onUnlock} />);
  expect(onUnlock).toHaveBeenCalledTimes(1);
});
