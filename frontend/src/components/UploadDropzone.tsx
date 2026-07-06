import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { uploadDocument } from "../api/ingest";

interface UploadDropzoneProps {
  onUploaded: () => void;
}

export default function UploadDropzone({ onUploaded }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(files: FileList | File[]) {
    setError(null);
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file);
      }
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      void upload(e.dataTransfer.files);
    }
  }

  function handlePick(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files.length > 0) {
      void upload(e.target.files);
      e.target.value = "";
    }
  }

  return (
    <div
      className={
        "dropzone" +
        (dragOver ? " drag-over" : "") +
        (uploading ? " uploading" : "")
      }
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        hidden
        onChange={handlePick}
      />
      <p className="dropzone-label">
        {uploading
          ? "Uploading…"
          : "Drag & drop PDFs here, or click to choose files"}
      </p>
      {error && <p className="dropzone-error">{error}</p>}
    </div>
  );
}
