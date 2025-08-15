import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

export default function App() {
  const [file, setFile] = useState(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [readme, setReadme] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState([]);
  const eventSourceRef = useRef(null);

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setReadme("");
    setLogs([]);

    // Start listening to progress
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    eventSourceRef.current = new EventSource(
      "http://localhost:8000/progress-stream"
    );
    eventSourceRef.current.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    const formData = new FormData();
    if (file) formData.append("file", file);
    if (repoUrl) formData.append("repo_url", repoUrl);

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/generate-readme`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await res.json();

      if (data.error) {
        setError(data.error);
      } else {
        setReadme(data.readme || "");
      }
    } catch (err) {
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    }
  };

  const handleDownload = () => {
    const blob = new Blob([readme], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "README.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white flex items-center justify-center p-6">
      <div className="bg-gray-850 rounded-2xl shadow-xl p-8 w-full max-w-3xl border border-gray-700">
        {/* Title */}
        <h1 className="text-4xl font-bold mb-6 flex items-center gap-2 justify-center">
          ⚡ Fancy AI README Generator
        </h1>

        {/* File Upload */}
        <div className="mb-6 flex flex-col items-center gap-3">
          <label
            htmlFor="file-upload"
            className="cursor-pointer bg-gradient-to-r from-purple-500 to-blue-500 px-6 py-3 rounded-lg font-medium shadow hover:opacity-90 transition"
          >
            📁 Upload ZIP File
          </label>
          <span className="text-gray-400 text-sm">
            {file ? file.name : "No file chosen"}
          </span>
          <input
            id="file-upload"
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files[0])}
            className="hidden"
          />
        </div>

        {/* Repo URL */}
        <div className="mb-6">
          <label className="block mb-2 font-semibold">
            🌐 Or enter GitHub repo URL:
          </label>
          <input
            type="text"
            placeholder="https://github.com/user/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            className="w-full p-3 rounded text-black"
          />
        </div>

        {/* Generate Button */}
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full bg-gradient-to-r from-green-400 to-teal-500 hover:opacity-90 transition px-4 py-3 rounded-lg font-semibold"
        >
          {loading ? "✨ Generating..." : "🚀 Generate Fancy README"}
        </button>

        {/* Progress Terminal */}
        {loading && (
          <div className="mt-6 bg-black p-4 rounded-lg font-mono text-green-400 h-40 overflow-y-auto border border-green-500">
            {logs.length === 0 && <div>🔄 Starting generation...</div>}
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 bg-red-600/30 p-3 rounded border border-red-500">
            ❌ {error}
          </div>
        )}

        {/* Preview */}
        {readme && (
          <div className="mt-6 bg-gray-900/80 p-4 rounded-lg border border-gray-700 max-h-96 overflow-y-auto">
            <h2 className="text-xl font-semibold mb-3">
              📄 Generated README Preview:
            </h2>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{readme}</ReactMarkdown>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="mt-4 bg-green-500 hover:bg-green-600 px-4 py-2 rounded"
            >
              ⬇️ Download README
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
