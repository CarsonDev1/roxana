import type { Metadata } from "next";
import { SourceList } from "@/components/SourceList";
import { NoData, PageTitle } from "@/components/ui";
import { getData } from "@/lib/data";
import type { SourceSort } from "@/lib/filter";
import { first, sourceOptions } from "@/lib/options";
import { excerpt } from "@/lib/text";

export const metadata: Metadata = { title: "Bài viết & nguồn" };

export default async function SourcesPage({ searchParams }: PageProps<"/bai-viet">) {
  const data = await getData();
  if (!data) return <NoData />;
  const sp = await searchParams;
  const initial = {
    q: first(sp.q), platform: first(sp.platform), container: first(sp.container), tone: first(sp.tone),
    importance: first(sp.importance), party: first(sp.party), topic: first(sp.topic),
    status: first(sp.status), sort: first(sp.sort) as SourceSort | undefined,
  };
  // Danh sách chỉ cần phần tóm tắt; bỏ các trường nặng để trang nhẹ. Nguyên văn chỉ giữ đoạn đầu mà danh sách hiển thị
  // (tìm kiếm dùng trường search, đã chứa toàn bộ nội dung).
  const light = data.sources.map((s) => ({ ...s, text: excerpt(s.current_text ?? s.text, 260), current_text: null,
    captures: [], attachments: null, metrics_history: [], notes: null }));
  return (
    <>
      <PageTitle title="Bài viết & nguồn" subtitle="Mỗi mục là một bài Facebook hoặc bài báo. Bấm để xem ảnh bằng chứng, nguyên văn và bình luận." />
      <SourceList sources={light} labels={data.labels} options={sourceOptions(data)} initial={initial} />
    </>
  );
}
