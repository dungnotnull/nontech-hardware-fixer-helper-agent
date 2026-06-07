"use client";

import { useState } from "react";
import Link from "next/link";
import { Camera, Wrench, ShieldCheck, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">FixerAgent</h1>
        <p className="mt-4 text-lg text-gray-600">AI-powered repair assistant for home appliances and electronics.</p>
      </div>
      <div className="grid gap-6 sm:grid-cols-2">
        <Link href="/diagnose" className="group rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition hover:shadow-md">
          <div className="mb-4 inline-flex rounded-lg bg-green-50 p-3 text-green-600"><Camera className="h-6 w-6" /></div>
          <h2 className="text-xl font-semibold text-gray-900">Start Diagnosis</h2>
          <p className="mt-2 text-sm text-gray-500">Upload a photo or describe the problem. Get a personalized repair guide in seconds.</p>
        </Link>
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 inline-flex rounded-lg bg-amber-50 p-3 text-amber-600"><ShieldCheck className="h-6 w-6" /></div>
          <h2 className="text-xl font-semibold text-gray-900">Safety First</h2>
          <p className="mt-2 text-sm text-gray-500">Every guide is rated by risk level. We auto-escalate mains voltage and gas-line repairs to certified technicians.</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 inline-flex rounded-lg bg-green-50 p-3 text-green-600"><Wrench className="h-6 w-6" /></div>
          <h2 className="text-xl font-semibold text-gray-900">Step-by-Step</h2>
          <p className="mt-2 text-sm text-gray-500">Clear, illustrated instructions grounded in manufacturer manuals and curated repair knowledge.</p>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 inline-flex rounded-lg bg-green-50 p-3 text-green-600"><Zap className="h-6 w-6" /></div>
          <h2 className="text-xl font-semibold text-gray-900">Always Learning</h2>
          <p className="mt-2 text-sm text-gray-500">Our knowledge base updates weekly from research papers, iFixit guides, and manufacturer bulletins.</p>
        </div>
      </div>
    </main>
  );
}