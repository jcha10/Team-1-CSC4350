import { afterEach, expect, it, vi } from "vitest";
import { api, session } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

it("getLeaderboard calls the right URL with the login token", async () => {
  // Fake the server so no backend is needed
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [{ username: "bob", value: 12, is_you: false }],
  });
  vi.stubGlobal("fetch", fetchMock);
  session.set("abc123");

  const rows = await api.getLeaderboard("apm");

  const [url, options] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/leaderboard/apm");
  expect(options.headers.Authorization).toBe("Bearer abc123");
  expect(rows[0].username).toBe("bob");
});
