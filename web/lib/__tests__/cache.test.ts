import { describe, expect, it, vi } from "vitest";
import { keyedCache } from "../cache";

describe("keyedCache", () => {
  it("loads once while the key is unchanged and the entry is fresh", async () => {
    let t = 0;
    const cache = keyedCache<number>(1000, () => t);
    const load = vi.fn(async () => 1);
    await cache("a", load);
    t = 999;
    await cache("a", load);
    expect(load).toHaveBeenCalledTimes(1);
  });
  it("shares one in-flight load between concurrent callers", async () => {
    const cache = keyedCache<number>(1000);
    const load = vi.fn(async () => 1);
    await Promise.all([cache("a", load), cache("a", load)]);
    expect(load).toHaveBeenCalledTimes(1);
  });
  it("reloads when the key changes or the entry expires", async () => {
    let t = 0;
    const cache = keyedCache<number>(1000, () => t);
    const load = vi.fn(async () => 1);
    await cache("a", load);
    await cache("b", load);
    t = 1000;
    await cache("b", load);
    expect(load).toHaveBeenCalledTimes(3);
  });
  it("does not keep a failed load", async () => {
    const cache = keyedCache<number>(1000);
    await expect(cache("a", async () => { throw new Error("down"); })).rejects.toThrow("down");
    await expect(cache("a", async () => 2)).resolves.toBe(2);
  });
});
