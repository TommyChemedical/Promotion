import { api, type ResearchArea } from "@/lib/api";
import { ResearchAreaList } from "@/components/research-map/ResearchAreaList";

export const dynamic = "force-dynamic";
export const metadata = { title: "Research-Map – LiteraturKI" };

export default async function ResearchMapPage() {
  let areas: ResearchArea[] = [];
  try {
    areas = await api.listResearchAreas();
  } catch {
    // backend unreachable — render with empty list
  }
  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-6">Research-Map</h1>
      <ResearchAreaList initialAreas={areas} />
    </div>
  );
}
