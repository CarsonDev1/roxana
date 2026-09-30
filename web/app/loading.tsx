// Hiện khi chuyển trang: các trang đều render lúc có request, nên có file này thì bấm menu thấy phản hồi ngay
// và Next prefetch sẵn được khung chờ (route động không có loading.tsx thì không được prefetch).
// Phủ vùng nội dung, nằm dưới thanh menu (header z-40) để vẫn bấm được mục khác trong lúc chờ.
export default function Loading() {
  return (
    <div role="status" aria-live="polite"
      className="fixed inset-0 z-30 flex items-center justify-center bg-page/60 backdrop-blur-[1px] page-loading">
      <div className="flex flex-col items-center gap-3 rounded-xl border border-line bg-surface px-6 py-5 shadow-sm">
        <span aria-hidden="true"
          className="size-9 rounded-full border-[3px] border-accent-wash border-t-accent motion-safe:animate-spin" />
        <span className="text-sm font-medium text-ink-2">Đang tải trang…</span>
      </div>
    </div>
  );
}
