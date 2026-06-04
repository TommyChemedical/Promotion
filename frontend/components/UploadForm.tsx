"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type UploadStatus = "idle" | "uploading" | "done" | "error";

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      await api.uploadSource(file);
      setStatus("done");
      setTimeout(() => router.push("/sources"), 1200);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload fehlgeschlagen.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="pdf-upload" className="block text-sm font-medium text-gray-700 mb-1">
          PDF-Datei auswählen
        </label>
        <input
          id="pdf-upload"
          type="file"
          accept=".pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-gray-700 border border-gray-300 rounded-md px-3 py-2 bg-white file:mr-3 file:py-1 file:px-3 file:border-0 file:text-sm file:font-medium file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
        />
      </div>

      {file && (
        <p className="text-sm text-gray-500">
          Ausgewählt: <span className="font-medium">{file.name}</span>{" "}
          ({(file.size / 1024).toFixed(0)} KB)
        </p>
      )}

      <button
        type="submit"
        disabled={!file || status === "uploading"}
        className="px-4 py-2 bg-gray-800 text-white text-sm rounded-md disabled:opacity-50 hover:bg-gray-700 transition-colors"
      >
        {status === "uploading" ? "Wird hochgeladen…" : "Hochladen"}
      </button>

      {status === "done" && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
          Erfolgreich hochgeladen. Weiterleitung zur Quellenliste…
        </p>
      )}

      {status === "error" && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          Fehler: {error}
        </p>
      )}
    </form>
  );
}
