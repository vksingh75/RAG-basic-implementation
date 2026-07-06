import { useState } from "react";
import UploadDropzone from "../components/UploadDropzone";
import DocumentTable from "../components/DocumentTable";

export default function UploadPage() {
  const [refreshToken, setRefreshToken] = useState(0);

  return (
    <div className="upload-page">
      <h1>Documents</h1>
      <UploadDropzone onUploaded={() => setRefreshToken((n) => n + 1)} />
      <DocumentTable refreshToken={refreshToken} />
    </div>
  );
}
