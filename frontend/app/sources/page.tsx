import Link from "next/link";
import { api } from "@/lib/api";
import { SourceCard } from "@/components/SourceCard";

export const dynamic = "force-dynamic";

export default async function SourcesPage() {
  let sources = [];
  try {
    sources = await api.getSources();
  } catch {
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Quellen</h1>
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-md px-4 py-3">
          Backend nicht erreichbar. Bitte starten Sie den Server unter{" "}
          <code className="font-mono">http://localhost:8000</code>.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold">
          Quellen{" "}
          <span className="text-gray-400 font-normal text-lg">({sources.length})</span>
        </h1>
        <Link
          href="/upload"
          className="text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md hover:bg-gray-700 transition-colors"
        >
          + Hochladen
        </Link>
      </div>

      {sources.length === 0 ? (
        <p className="text-gray-500 text-sm">
          Noch keine Quellen vorhanden.{" "}
          <Link href="/upload" className="underline hover:text-gray-700">
            Jetzt hochladen.
          </Link>
        </p>
      ) : (
        <div className="space-y-3">
          {sources.map((source) => (
            <SourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
