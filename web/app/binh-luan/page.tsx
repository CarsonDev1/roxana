import type { Metadata } from "next";
import { CommentList } from "@/components/CommentList";
import { NoData, PageTitle } from "@/components/ui";
import { getData } from "@/lib/data";
import { commentOptions, first } from "@/lib/options";

export const metadata: Metadata = { title: "Bình luận" };

export default async function CommentsPage({ searchParams }: PageProps<"/binh-luan">) {
  const data = await getData();
  if (!data) return <NoData />;
  const sp = await searchParams;
  const titles = Object.fromEntries(data.sources.map((s) => [s.id, `${s.author_name}${s.container_name ? ` · ${s.container_name}` : ""}`]));
  return (
    <>
      <PageTitle title="Bình luận" subtitle="Mọi bình luận và trả lời đã thu, theo thứ tự cây của từng bài. Mức thấp vẫn được ghi đủ nguyên văn." />
      <CommentList comments={data.comments} labels={data.labels} options={commentOptions(data)} sourceTitles={titles}
        initial={{ q: first(sp.q), tone: first(sp.tone), importance: first(sp.importance), party: first(sp.party), source: first(sp.source) }} />
    </>
  );
}
