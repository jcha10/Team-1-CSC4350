import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, renderHook } from "@testing-library/react";
import useLiveSocket from "./useLiveSocket";

// A fake WebSocket that records every connection the hook opens.
class FakeSocket {
  static opened = [];
  constructor(url) {
    this.url = url;
    FakeSocket.opened.push(this);
  }
  close() {}
}

beforeEach(() => {
  FakeSocket.opened = [];
  vi.stubGlobal("WebSocket", FakeSocket);
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("reconnects after a dropped connection", () => {
  renderHook(() => useLiveSocket(() => "ws://test/ws/leaderboard"));
  expect(FakeSocket.opened).toHaveLength(1);

  FakeSocket.opened[0].onclose({ code: 1006 }); // the connection dropped
  vi.advanceTimersByTime(1000); // the first retry waits 1 second
  expect(FakeSocket.opened).toHaveLength(2);
});

it("stops for good after a 1008 (not authorized) close", () => {
  const onUnauthorized = vi.fn();
  renderHook(() => useLiveSocket(() => "ws://test/ws/leaderboard", { onUnauthorized }));

  FakeSocket.opened[0].onclose({ code: 1008 });
  vi.advanceTimersByTime(60000); // wait a full minute: still no retry
  expect(FakeSocket.opened).toHaveLength(1);
  expect(onUnauthorized).toHaveBeenCalledOnce();
});
