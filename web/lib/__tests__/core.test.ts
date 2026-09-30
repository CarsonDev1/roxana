import { describe, expect, it } from "vitest";
import path from "node:path";
import { allowedFile } from "../files";
import { filterComments, filterSources } from "../filter";
import { fmtTime, fold } from "../text";
import type { Comment, Source } from "../types";

const ROOT = path.resolve("/proj");

describe("allowedFile", () => {
  it("accepts files inside the three evidence folders", () => {
    expect(allowedFile(ROOT, "screenshots/facebook/2026-09-30/FB-P00012_post_01.png")).toBe(
      path.join(ROOT, "screenshots", "facebook", "2026-09-30", "FB-P00012_post_01.png"));
    expect(allowedFile(ROOT, "snapshots/facebook/2026-09-30/FB-P00012.txt")).not.toBeNull();
    expect(allowedFile(ROOT, "output/thumbs/x_w240.jpg")).not.toBeNull();
  });
  it.each([
    "../config.json", "config.json", "data/records.jsonl", "screenshots/../config.json",
    "output/site/data.json", "output/thumbs/../../config.json", "/etc/passwd", "C:/Windows/win.ini",
    "screenshots\\..\\config.json", "", "screenshots",
  ])("rejects %s", (p) => {
    expect(allowedFile(ROOT, p)).toBeNull();
  });
});

describe("fold", () => {
  it("matches the Python fold (accents, đ, case, spaces)", () => {
    expect(fold("  Phạm   Thị NGỌC Liên ")).toBe("pham thi ngoc lien");
    expect(fold("Đòi nhà")).toBe("doi nha");
    expect(fold("Pha\u0323m")).toBe("pham"); // NFD input
  });
});

describe("fmtTime", () => {
  it("formats by precision in +07:00", () => {
    expect(fmtTime("2026-08-22T13:37:00+07:00", "exact")).toBe("22/08/2026 13:37");
    expect(fmtTime("2026-08-22T00:00:00+07:00", "day")).toBe("22/08/2026");
    expect(fmtTime("2026-08-01T00:00:00+07:00", "month")).toBe("08/2026");
    expect(fmtTime("2026-01-01T00:00:00+07:00", "year")).toBe("2026");
    expect(fmtTime("2026-08-22T06:37:00Z", "exact")).toBe("22/08/2026 13:37");
    expect(fmtTime(null)).toBe("");
  });
});

const src = (over: Partial<Source>): Source => ({
  id: "FB-P00001", platform: "facebook", tone: "tieu_cuc", importance: "trung_binh", origin: "scan",
  status: "active", container_id: "FB-G0001", entities_mentioned: [], topics: [], keywords_matched: [],
  posted_at: "2026-08-22T13:37:00+07:00", captured_at: "2026-09-30T10:00:00+07:00", search: "",
  ...over,
} as Source);

describe("filterSources", () => {
  const list = [
    src({ id: "A", search: "de cho 4 5 dua lien", tone: "gay_gat", importance: "cao", entities_mentioned: ["lien"],
          posted_at: "2026-08-22T13:37:00+07:00" }),
    src({ id: "B", search: "noi hoi tu tinh hoa", platform: "web", posted_at: "2024-12-02T12:22:00+07:00" }),
    src({ id: "C", search: "khong ro ngay", posted_at: null, topics: ["toa_an"] }),
  ];
  it("searches accent-insensitively", () => {
    expect(filterSources(list, { q: "Liên" }).map((s) => s.id)).toEqual(["A"]);
    expect(filterSources(list, { q: "tinh hoa" }).map((s) => s.id)).toEqual(["B"]);
  });
  it("filters by facets", () => {
    expect(filterSources(list, { tone: "gay_gat" }).map((s) => s.id)).toEqual(["A"]);
    expect(filterSources(list, { platform: "web" }).map((s) => s.id)).toEqual(["B"]);
    expect(filterSources(list, { party: "lien" }).map((s) => s.id)).toEqual(["A"]);
    expect(filterSources(list, { topic: "toa_an" }).map((s) => s.id)).toEqual(["C"]);
  });
  it("sorts newest posted first, unknown dates last", () => {
    expect(filterSources(list, {}, "posted_desc").map((s) => s.id)).toEqual(["A", "B", "C"]);
    expect(filterSources(list, {}, "posted_asc").map((s) => s.id)).toEqual(["B", "A", "C"]);
  });
});

describe("filterComments", () => {
  const c = (id: string, over: Partial<Comment>): Comment =>
    ({ id, source_id: "S", search: "", tone: "trung_lap", importance: "thap", entities_mentioned: [], order: 0,
       ...over } as Comment);
  it("keeps tree order and filters", () => {
    const list = [c("1", { order: 0, search: "tra nha di" }), c("2", { order: 1, importance: "cao" })];
    expect(filterComments(list, { importance: "cao" }).map((x) => x.id)).toEqual(["2"]);
    expect(filterComments(list, { q: "trả nhà" }).map((x) => x.id)).toEqual(["1"]);
  });
});
