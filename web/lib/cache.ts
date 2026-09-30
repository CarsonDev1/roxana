/**
 * Giữ kết quả của `load` trong bộ nhớ của tiến trình server cho tới khi `key` đổi hoặc quá `ttlMs`.
 * Các lần gọi cùng lúc dùng chung một lần tải; lần tải lỗi không được giữ lại.
 */
export function keyedCache<T>(ttlMs: number, now: () => number = Date.now) {
  let entry: { key: string; at: number; value: Promise<T> } | null = null;
  return (key: string, load: () => Promise<T>): Promise<T> => {
    if (entry && entry.key === key && now() - entry.at < ttlMs) return entry.value;
    const current = { key, at: now(), value: load() };
    entry = current;
    current.value.catch(() => {
      if (entry === current) entry = null;
    });
    return current.value;
  };
}
