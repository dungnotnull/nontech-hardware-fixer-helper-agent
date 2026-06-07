"use client";

import { useState, useCallback } from "react";
import ImageUpload from "@/components/ImageUpload";
import DiagnosisProgress from "@/components/DiagnosisProgress";
import RepairGuide from "@/components/RepairGuide";
import FeedbackForm from "@/components/FeedbackForm";
import { diagnose } from "@/lib/api";

export default function DiagnosePage() {
  const [image, setImage] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [deviceHint, setDeviceHint] = useState("");
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      if (image) formData.append("image", image);
      formData.append("description", description);
      formData.append("device_hint", deviceHint);
      const data = await diagnose(formData);
      setResult(data);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "Diagnosis failed");
    } finally {
      setLoading(false);
    }
  }, [image, description, deviceHint]);

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="mb-6 text-3xl font-bold text-gray-900">Diagnose Your Device</h1>
      <div className="space-y-4">
        <ImageUpload onFileSelect={setImage} />
        <textarea
          className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-green-500 focus:outline-none"
          rows={3}
          placeholder="Describe the problem..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-green-500 focus:outline-none"
          placeholder="Device hint (optional)"
          value={deviceHint}
          onChange={(e) => setDeviceHint(e.target.value)}
        />
        <button
          onClick={handleSubmit}
          disabled={loading || (!image && !description)}
          className="w-full rounded-lg bg-green-600 px-4 py-3 font-medium text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {loading ? "Analyzing..." : "Get Repair Guide"}
        </button>
      </div>
      {loading && <DiagnosisProgress />}
      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {result && <RepairGuide result={result} />}
      {result?.session_id && <FeedbackForm sessionId={result.session_id} />}
    </main>
  );
}