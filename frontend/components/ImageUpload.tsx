"use client";

import { useCallback } from "react";
import { UploadCloud } from "lucide-react";

interface Props {
  onFileSelect: (file: File | null) => void;
}

export default function ImageUpload({ onFileSelect }: Props) {
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) onFileSelect(file);
  }, [onFileSelect]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    onFileSelect(file);
  }, [onFileSelect]);

  return (
    <label
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 transition hover:border-green-400 hover:bg-green-50"
    >
      <UploadCloud className="mb-2 h-8 w-8 text-gray-400" />
      <p className="text-sm font-medium text-gray-600">Click or drag a photo here</p>
      <p className="mt-1 text-xs text-gray-400">JPEG, PNG up to 10MB</p>
      <input type="file" accept="image/*" className="hidden" onChange={handleChange} />
    </label>
  );
}