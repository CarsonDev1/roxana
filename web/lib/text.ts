// Text helpers shared by server and client components. fold() mirrors common.fold() in Python.

export function fold(text: string | null | undefined): string {
  return (text ?? "")
    .normalize("NFC")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .normalize("NFD")
    .replace(/\p{Mn}/gu, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

const TZ_OFFSET_MIN = 7 * 60; // mọi thời gian hiển thị theo +07:00

function parts(value: string) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const t = new Date(d.getTime() + TZ_OFFSET_MIN * 60_000);
  const p = (n: number) => String(n).padStart(2, "0");
  return { y: t.getUTCFullYear(), m: p(t.getUTCMonth() + 1), d: p(t.getUTCDate()), hh: p(t.getUTCHours()),
    mm: p(t.getUTCMinutes()) };
}

export function fmtTime(value: string | null | undefined, precision?: string | null): string {
  if (!value) return "";
  const t = parts(value);
  if (!t) return value;
  if (precision === "year") return `${t.y}`;
  if (precision === "month") return `${t.m}/${t.y}`;
  if (precision === "day") return `${t.d}/${t.m}/${t.y}`;
  return `${t.d}/${t.m}/${t.y} ${t.hh}:${t.mm}`;
}

export function fmtMonth(month: string): string {
  if (month === "unknown") return "Không rõ";
  const [y, m] = month.split("-");
  return `${m}/${y}`;
}

export function fmtNumber(n: number | null | undefined): string {
  return n == null ? "—" : n.toLocaleString("vi-VN");
}

export function excerpt(text: string | null | undefined, n = 220): string {
  const t = (text ?? "").replace(/\s+/g, " ").trim();
  return t.length <= n ? t : t.slice(0, n).trimEnd() + "…";
}

// Ký tự điều khiển trong nguyên văn (vd \x0b) không được làm vỡ hiển thị; giữ nguyên dữ liệu, chỉ thay khi vẽ.
export function displayText(text: string | null | undefined): string {
  return (text ?? "").replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "�");
}
