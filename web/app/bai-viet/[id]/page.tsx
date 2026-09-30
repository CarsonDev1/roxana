import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { CommentTree } from "@/components/CommentTree";
import { Thumb } from "@/components/Thumb";
import { Badge, Card, Ext, ImportanceBadge, KeyVal, NoData, SectionTitle, StatusBadge, ToneBadge } from "@/components/ui";
import { getData, keywordLabel, label, partyLabel } from "@/lib/data";
import { fileUrl } from "@/lib/files";
import { displayText, fmtNumber, fmtTime } from "@/lib/text";

export async function generateMetadata({ params }: PageProps<"/bai-viet/[id]">): Promise<Metadata> {
  return { title: (await params).id };
}

export default async function SourcePage({ params }: PageProps<"/bai-viet/[id]">) {
  const { id } = await params;
  const data = await getData();
  if (!data) return <NoData />;
  const s = data.sources.find((x) => x.id === id);
  if (!s) {
    const replacement = data.sources.find((x) => x.supersedes === id);
    if (replacement) redirect(`/bai-viet/${replacement.id}`);
    notFound();
  }
  const L = (e: string, v: string | null | undefined) => label(data, e, v);
  const P = (pid: string) => partyLabel(data, pid);
  const comments = data.comments.filter((c) => c.source_id === s.id);
  const changes = data.changes.filter((c) => c.target_id === s.id || comments.some((x) => x.id === c.target_id));
  const container = data.containers.find((c) => c.id === s.container_id);
  const m = s.metrics;

  return (
    <article>
      <nav className="no-print mb-3 text-sm"><Link href="/bai-viet" className="text-accent-ink hover:underline">← Tất cả bài</Link></nav>

      <header className="mb-5">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{s.author_name}</h1>
          {s.author_badge && <Badge tone="neutral">{s.author_badge}</Badge>}
          <span className="font-mono text-sm text-muted">{s.id}</span>
        </div>
        <p className="mt-1 text-sm text-ink-2">
          {L("content_type", s.content_type)}
          {s.container_name && <> trong {container ? <Link className="text-accent-ink hover:underline" href={`/bai-viet?container=${container.id}`}>{s.container_name}</Link> : s.container_name}</>}
          {" · "}{fmtTime(s.posted_at, s.posted_at_precision) || s.posted_at_raw || "không rõ ngày"}
          {" · "}{L("platform", s.platform)}
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          <ImportanceBadge value={s.importance} label={L("importance", s.importance)} />
          <ToneBadge value={s.tone} label={L("tone", s.tone)} />
          {s.claim_type && <Badge tone="neutral">{L("claim_type", s.claim_type)}</Badge>}
          <StatusBadge value={s.status} label={L("recheck_status", s.status)} />
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <Card>
            <SectionTitle>Nội dung nguyên văn</SectionTitle>
            {s.status === "edited" && s.current_text != null && (
              <div className="mb-3 rounded-lg bg-warning-wash p-3 text-sm">
                <p className="font-medium"><span aria-hidden="true">✎ </span>Nội dung đã bị sửa — bản mới nhất:</p>
                <p className="prose-raw mt-1">{displayText(s.current_text)}</p>
                <p className="mt-2 text-xs text-ink-2">Bản gốc lúc thu thập giữ nguyên bên dưới.</p>
              </div>
            )}
            {s.text ? <p className="prose-raw text-[15px] leading-relaxed">{displayText(s.text)}</p>
              : <p className="text-sm italic text-muted">(bài chỉ có ảnh)</p>}
            {(s.attachments ?? []).length > 0 && (
              <div className="mt-4 space-y-3">
                <h3 className="text-sm font-semibold">Đính kèm</h3>
                {(s.attachments ?? []).map((a, i) => (
                  <div key={i} className="rounded-lg bg-surface-2 p-3 text-sm">
                    <p><span className="text-muted">[{a.kind}]</span> {a.description}</p>
                    {a.transcribed_text && (
                      <details className="mt-2" open={(a.transcribed_text?.length ?? 0) < 600}>
                        <summary className="cursor-pointer text-xs font-medium text-ink-2">Chữ trong ảnh (chép lại)</summary>
                        <p className="prose-raw mt-1 text-[13px]">{displayText(a.transcribed_text)}</p>
                      </details>
                    )}
                    {a.url && <p className="mt-1 text-xs"><Ext href={a.url}>Mở ảnh trên Facebook</Ext></p>}
                  </div>
                ))}
              </div>
            )}
            {s.shared_from && (
              <p className="mt-3 text-sm text-ink-2">Chia sẻ từ: {s.shared_from.author_name} — {s.shared_from.text_excerpt} <Ext href={s.shared_from.url} /></p>
            )}
          </Card>

          <Card>
            <SectionTitle>Ảnh bằng chứng</SectionTitle>
            {s.captures.length === 0 ? <p className="text-sm text-muted">Chưa có ảnh chụp.</p> : (
              <div className="space-y-5">
                {/* Chỉ hiện lần chụp mới nhất: lần trước có thể là ảnh toàn màn hình (dính thông tin tài khoản quét)
                    — vẫn giữ trong kho làm bằng chứng nhưng không hiển thị. */}
                {s.captures.slice(-1).map((cap) => (
                  <div key={cap.record_id}>
                    <p className="mb-2 text-xs text-muted">Lần chụp mới nhất · {cap.record_id} · {fmtTime(cap.at)}</p>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                      {cap.images.filter(Boolean).map((img) => (
                        <figure key={img!.file} className="space-y-1">
                          <Thumb image={img} alt={img!.shows ?? img!.kind} />
                          <figcaption className="text-xs">
                            <span className="font-medium">{L("evidence_kind", img!.kind)}</span>
                            {img!.shows && <span className="text-ink-2"> — {img!.shows}</span>}
                            <span className="block text-muted">Chụp {fmtTime(img!.captured_at)} · {img!.capture_tool}</span>
                            <span className="block break-all font-mono text-[10px] text-muted">SHA-256 {img!.sha256}</span>
                          </figcaption>
                        </figure>
                      ))}
                    </div>
                  </div>
                ))}
                {s.captures.length > 1 && (
                  <p className="text-xs text-muted">
                    Còn {s.captures.length - 1} lần chụp trước ({s.captures.slice(0, -1).map((c) => `${c.record_id} · ${fmtTime(c.at)}`).join("; ")})
                    lưu trong kho làm bằng chứng — không hiển thị ở đây.
                  </p>
                )}
              </div>
            )}
          </Card>

          <section aria-labelledby="bl">
            <SectionTitle id="bl">Bình luận đã thu ({comments.length}{m.comments != null ? ` / Facebook hiển thị ${m.comments}` : ""})</SectionTitle>
            {comments.length === 0 ? <p className="text-sm text-muted">Chưa thu bình luận.</p>
              : <CommentTree comments={comments} L={L} partyLabel={P} />}
          </section>
        </div>

        <aside className="space-y-5">
          <Card>
            <SectionTitle>Thông tin</SectionTitle>
            <KeyVal items={[
              ["Link bài", <Ext key="u" href={s.url} />],
              ["Loại link", L("url_kind", s.url_kind)],
              ["Người đăng", <>{s.author_name} {s.author_url && <Ext href={s.author_url}>(trang)</Ext>}</>],
              ["Loại tài khoản", L("author_kind", s.author_kind)],
              ["Thời gian (gốc)", s.posted_at_raw],
              ["Ngày đăng", fmtTime(s.posted_at, s.posted_at_precision)],
              ["Độ chính xác", L("posted_at_precision", s.posted_at_precision)],
              ["Thu thập lúc", fmtTime(s.captured_at)],
              ["Lần quét", s.run_id],
              ["Kiểm tra lần cuối", fmtTime(s.last_checked_at)],
              ["Bản chữ gốc", s.snapshot_file ? <a key="snap" className="text-accent-ink hover:underline" href={fileUrl(s.snapshot_file)!} target="_blank" rel="noopener">Mở bản chữ</a> : null],
            ]} />
          </Card>
          <Card>
            <SectionTitle>Tương tác</SectionTitle>
            <div className="grid grid-cols-3 gap-2 text-center">
              {([["Cảm xúc", m.reactions], ["Bình luận", m.comments], ["Chia sẻ", m.shares]] as const).map(([k, v]) => (
                <div key={k} className="rounded-lg bg-surface-2 p-2"><p className="text-lg font-semibold">{fmtNumber(v)}</p><p className="text-xs text-muted">{k}</p></div>
              ))}
            </div>
            {m.counted_at && <p className="mt-2 text-xs text-muted">Đếm lúc {fmtTime(m.counted_at)}</p>}
          </Card>
          <Card>
            <SectionTitle>Phân loại</SectionTitle>
            <KeyVal items={[
              ["Từ khoá", s.keywords_matched.map((k) => keywordLabel(data, k)).join(", ")],
              ["Bên được nhắc", (s.entities_mentioned ?? []).map(P).join(", ")],
              ["Chủ đề", (s.topics ?? []).map((t) => L("topics", t)).join(", ")],
              ["Thái độ", L("tone", s.tone)],
              ["Loại nội dung", L("claim_type", s.claim_type)],
              ["Mức quan trọng", L("importance", s.importance)],
              ["Lý do", s.importance_reason],
            ]} />
            <p className="mt-3 text-xs text-muted">Phân loại chỉ mô tả nội dung, không phải kết luận pháp lý.</p>
          </Card>
          {changes.length > 0 && (
            <Card>
              <SectionTitle>Lịch sử kiểm tra lại</SectionTitle>
              <ol className="space-y-2 text-sm">
                {changes.map((c) => (
                  <li key={c.id} className="border-l-2 border-line pl-3">
                    <p><span className="font-mono text-xs text-muted">{c.id}</span> · {fmtTime(c.checked_at)} · {L("recheck_status", c.status)}
                      {c.target_id !== s.id && <> · <a className="text-accent-ink hover:underline" href={`#${c.target_id}`}>{c.target_id}</a></>}</p>
                    {c.new_text && <p className="prose-raw text-ink-2">{displayText(c.new_text)}</p>}
                    {c.notes && <p className="text-xs text-muted">{c.notes}</p>}
                  </li>
                ))}
              </ol>
            </Card>
          )}
          {s.notes && <Card><SectionTitle>Ghi chú</SectionTitle><p className="prose-raw text-sm text-ink-2">{s.notes}</p></Card>}
        </aside>
      </div>
    </article>
  );
}
