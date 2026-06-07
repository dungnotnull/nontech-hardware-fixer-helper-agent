"use client";

import { Loader2 } from "lucide-react";

export default function DiagnosisProgress() {
  const steps = ["Analyzing image...", "Identifying device...", "Checking safety...", "Retrieving knowledge...", "Building guide..."];
  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-3">
        <Loader2 className="h-5 w-5 animate-spin text-green-600" />
        <span className="text-sm font-medium text-gray-700">Running diagnosis pipeline...</span>
      </div>
      <ul className="mt-4 space-y-2">
        {steps.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-xs text-gray-500">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-400" /> {s}
          </li>
        ))}
      </ul>
    </div>
  );
}