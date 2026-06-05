import { notFound } from "next/navigation";
import { api, type ResearchArea, type ResearchAreaOverview, type ResearchAreaFindingEntry } from "@/lib/api";
import { ResearchAreaDetailPage } from "./ResearchAreaDetailPage";

export const dynamic = "force-dynamic";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let area: ResearchArea;
  let overview: ResearchAreaOverview;
  let entries: ResearchAreaFindingEntry[];
  try {
    [area, overview, entries] = await Promise.all([
      api.getResearchArea(Number(id)),
      api.getResearchAreaOverview(Number(id)),
      api.listAreaFindings(Number(id), { include_unreviewed: true }),
    ]);
  } catch {
    notFound();
  }
  return (
    <ResearchAreaDetailPage
      area={area!}
      initialOverview={overview!}
      initialEntries={entries!}
    />
  );
}
