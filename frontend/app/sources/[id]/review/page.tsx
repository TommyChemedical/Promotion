import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { ReviewPage } from "./ReviewPage";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function SourceReviewPage({ params }: Props) {
  const { id } = await params;
  const sourceId = parseInt(id, 10);
  if (isNaN(sourceId)) notFound();

  const [source, reviewData] = await Promise.all([
    api.getSource(sourceId).catch(() => null),
    api.getSourceReview(sourceId).catch(() => null),
  ]);

  if (!source || !reviewData) notFound();

  return <ReviewPage source={source} reviewData={reviewData} />;
}
