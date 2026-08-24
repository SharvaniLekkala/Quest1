import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";
const imageUrl = (path) => new URL(path, API_URL).toString();

export default function App() {
  const [videoUrl, setVideoUrl] = useState("");
  const [target, setTarget] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_URL}/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl.trim(), target: target.trim() }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The video could not be processed.");
      }
      setResult(payload);
    } catch (requestError) {
      setError(requestError.message || "Unable to reach the API.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="card" aria-labelledby="page-title">
        <p className="eyebrow">Video search</p>
        <h1 id="page-title">Find a dialogue frame</h1>
        <p className="intro">Paste a public video URL and the line you want to locate.</p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="video-url">Public video URL</label>
          <input
            id="video-url"
            type="url"
            value={videoUrl}
            onChange={(event) => setVideoUrl(event.target.value)}
            placeholder="https://..."
            required
          />

          <label htmlFor="dialogue">Dialogue text</label>
          <textarea
            id="dialogue"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            placeholder="Enter the line of dialogue to find"
            rows="4"
            required
          />

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Finding frame…" : "Find frame"}
          </button>
        </form>

        {error && <p className="message error" role="alert">{error}</p>}

        {result && (
          <section className="result" aria-live="polite" aria-label="Detection result">
            <h2>Match found</h2>
            <dl>
              <div><dt>Timestamp</dt><dd>{result.timestamp}</dd></div>
              <div><dt>Frame number</dt><dd>{result.frame_number}</dd></div>
              <div className="full-width"><dt>Extracted text</dt><dd>{result.extracted_text}</dd></div>
            </dl>
            <img src={imageUrl(result.frame_image)} alt={`Frame at ${result.timestamp}`} />
          </section>
        )}
      </section>
    </main>
  );
}
