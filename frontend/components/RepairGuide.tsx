"use client";

import { AlertTriangle, CheckCircle, Clock, Wrench, Package } from "lucide-react";

interface Props {
  result: any;
}

export default function RepairGuide({ result }: Props) {
  const guide = result.guide;
  const status = result.status;

  if (status === "escalated") {
    return (
      <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-6">
        <div className="flex items-center gap-2 text-red-700">
          <AlertTriangle className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Professional Repair Required</h2>
        </div>
        <p className="mt-2 text-sm text-red-700">{result.message}</p>
        {result.safety?.warnings?.map((w: string, i: number) => (
          <p key={i} className="mt-1 text-sm text-red-600">• {w}</p>
        ))}
      </div>
    );
  }

  if (!guide) return null;

  const tierColors: Record<number, string> = {
    1: "bg-green-100 text-green-800",
    2: "bg-amber-100 text-amber-800",
    3: "bg-orange-100 text-orange-800",
    4: "bg-red-100 text-red-800",
  };

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${tierColors[guide.safety?.tier || 1]}`}>
          {guide.safety?.tier_label || "DIY Easy"}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500"><Clock className="h-3.5 w-3.5" /> {guide.estimated_total_time}</span>
      </div>

      <h2 className="text-xl font-bold text-gray-900">🔧 {guide.device_name} — {guide.fault_description}</h2>

      {guide.tools_needed?.length > 0 && (
        <div className="mt-3 flex items-start gap-2 text-sm text-gray-600">
          <Wrench className="mt-0.5 h-4 w-4 text-gray-400" />
          <span>Tools: {guide.tools_needed.join(", ")}</span>
        </div>
      )}
      {guide.parts_needed?.length > 0 && (
        <div className="mt-1 flex items-start gap-2 text-sm text-gray-600">
          <Package className="mt-0.5 h-4 w-4 text-gray-400" />
          <span>Parts: {guide.parts_needed.join(", ")}</span>
        </div>
      )}

      <div className="mt-4 space-y-4">
        {guide.steps?.map((step: any, idx: number) => (
          <div key={idx} className="rounded-lg border-l-4 border-green-500 bg-gray-50 p-4">
            <h3 className="font-semibold text-gray-900">Step {step.step_number}: {step.title}</h3>
            <p className="mt-1 text-sm text-gray-700">{step.instruction}</p>
            {step.estimated_time_min && <p className="mt-1 text-xs text-gray-500">⏱ ~{step.estimated_time_min} min</p>}
            {step.caution_notes?.length > 0 && (
              <div className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-800">
                ⚠️ {step.caution_notes.join(" ")}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg bg-green-50 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-green-800">
          <CheckCircle className="h-4 w-4" /> Test Procedure
        </div>
        <p className="mt-1 text-sm text-green-700">{guide.test_procedure}</p>
      </div>

      <p className="mt-4 text-xs text-gray-400">
        Source: {guide.source_attribution} • Confidence: {Math.round((guide.knowledge_confidence || 0) * 100)}%
      </p>
    </div>
  );
}