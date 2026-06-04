import { UploadForm } from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold mb-2">Neue Quelle hochladen</h1>
      <p className="text-sm text-gray-500 mb-6">
        Laden Sie eine wissenschaftliche PDF-Datei hoch. Text und Metadaten werden
        automatisch extrahiert.
      </p>
      <UploadForm />
    </div>
  );
}
