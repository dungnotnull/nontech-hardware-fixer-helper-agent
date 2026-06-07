"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, Minus } from "lucide-react";
import { submitFeedback } from "@/lib/api";

interface Props {
  sessionId: string;
}

export default function FeedbackForm({ sessionId }: Props) {
  const [outcome, setOutcome] = useState<"fixed" | "partial" | "failed" | null>(null);
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!outcome) return;
    try {
      await submitFeedback({ session_id: sessionId, outcome, notes });
      setSubmitted(true);
    } catch (e: any) {
      setError(e.message || "Failed to submit feedback");
    }
  };

  if (submitted) {
    return (
      <div className="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 text-center text-sm text-green-700">
        ✅ Thank you! Your feedback helps us improve.
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6">
      <h3 className="text-sm font-semibold text-gray-900">Did this guide help you fix the problem?</h3>
      <div className="mt-3 flex gap-3">
        {([
          { key: "fixed", label: "Fixed it", icon: ThumbsUp, color: "bg-green-600" },
          { key: "partial", label: "Partially", icon: Minus, color: "bg-amber-500" },
          { key: "failed", label: "Didn't work", icon: ThumbsDown, color: "bg-red-500" },
        ] as const).map((btn) => (
          <button
            key={btn.key}
            onClick={() => setOutcome(btn.key)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
              outcome === btn.key ? `${btn.color} text-white` : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            <btn.icon className="h-4 w-4" /> {btn.label}
          </button>
        ))}
      </div>
      <textarea
        className="mt-3 w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-green-500 focus:outline-none"
        rows={2}
        placeholder="Any additional notes? (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <button
        onClick={handleSubmit}
        disabled={!outcome}
        className="mt-3 w-full rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        Submit Feedback
      </button>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}