import { displayText, fmtTime } from "@/lib/text";
import type { Comment } from "@/lib/types";
import { ImageLink } from "./ImageViewer";
import { Thumb } from "./Thumb";
import { Badge, Ext, ImportanceBadge, StatusBadge, ToneBadge } from "./ui";

type L = (e: string, v: string | null | undefined) => string;

function CommentItem({ c, L, partyLabel }: { c: Comment; L: L; partyLabel: (id: string) => string }) {
  const refs = c.scroll_refs ?? [];
  return (
    <article id={c.id} aria-label={`Bình luận của ${c.author_name}`}
      className={`scroll-mt-24 rounded-xl border bg-surface p-3 ${c.importance === "cao" ? "border-critical/40" : "border-line"}`}>
      <header className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span className="font-semibold">{c.author_name}</span>
        {c.author_badge && <Badge tone="neutral">{c.author_badge}</Badge>}
        <span className="text-xs text-muted">
          {fmtTime(c.posted_at, c.posted_at_precision) || c.posted_at_raw}
          {c.posted_at_precision !== "exact" && c.posted_at_raw ? ` (${c.posted_at_raw})` : ""}
        </span>
        <span className="font-mono text-xs text-muted">{c.id}</span>
      </header>
      {c.text ? <p className="prose-raw mt-1.5 text-[15px]">{displayText(c.text)}</p>
        : <p className="mt-1.5 text-sm italic text-muted">(không có chữ)</p>}
      {(c.attachments ?? []).map((a, i) => (
        <p key={i} className="mt-1 text-sm text-ink-2">[{L("attachment_kind", a.kind) || a.kind}] {a.description}
          {a.transcribed_text && <span className="text-muted"> — “{a.transcribed_text}”</span>}</p>
      ))}
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <ImportanceBadge value={c.importance} label={L("importance", c.importance)} />
        <ToneBadge value={c.tone} label={L("tone", c.tone)} />
        {c.claim_type && <Badge tone="neutral">{L("claim_type", c.claim_type)}</Badge>}
        <StatusBadge value={c.status} label={L("recheck_status", c.status)} />
        {(c.entities_mentioned ?? []).map((p) => <Badge key={p} tone="accent">{partyLabel(p)}</Badge>)}
        {c.reactions ? <span className="text-xs text-muted">· {c.reactions} cảm xúc</span> : null}
      </div>
      {c.importance_reason && <p className="mt-1 text-xs text-ink-2">Lý do: {c.importance_reason}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        {refs.map((r) => (
          <ImageLink key={r.file + r.position} image={{ file: r.file, title: `Ảnh cuộn bình luận — ${c.author_name} ở vị trí ${r.position}` }}>
            Ảnh cuộn {r.file.split("/").pop()} · vị trí {r.position}
          </ImageLink>
        ))}
        {c.url && <Ext href={c.url}>Link bình luận</Ext>}
      </div>
      {c.own_image && (
        <div className="mt-2 max-w-xl">
          <Thumb image={c.own_image} alt={`Ảnh riêng bình luận ${c.id}`} big />
          <p className="mt-1 break-all font-mono text-[11px] text-muted">SHA-256 {c.own_image.sha256}</p>
        </div>
      )}
      {c.notes && <p className="mt-2 text-xs text-muted">Ghi chú: {c.notes}</p>}
    </article>
  );
}

export function CommentTree({ comments, L, partyLabel }:
  { comments: Comment[]; L: L; partyLabel: (id: string) => string }) {
  const children = new Map<string | null, Comment[]>();
  const ids = new Set(comments.map((c) => c.id));
  for (const c of comments) {
    const parent = c.parent_comment_id && ids.has(c.parent_comment_id) ? c.parent_comment_id : null;
    children.set(parent, [...(children.get(parent) ?? []), c]);
  }
  const render = (parent: string | null, level: number): React.ReactNode => (
    <ul className={level ? "mt-2 space-y-2 border-l-2 border-line pl-4" : "space-y-3"}>
      {(children.get(parent) ?? []).map((c) => (
        <li key={c.id}>
          <CommentItem c={c} L={L} partyLabel={partyLabel} />
          {children.has(c.id) && render(c.id, level + 1)}
        </li>
      ))}
    </ul>
  );
  return <>{render(null, 0)}</>;
}
