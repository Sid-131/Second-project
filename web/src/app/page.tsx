"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [pulse, setPulse] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(true);
  const [logs, setLogs] = useState<string>("");

  // Custom inputs
  const [weeks, setWeeks] = useState("8");
  const [email, setEmail] = useState("");
  const [topics, setTopics] = useState("");

  // UI state for search flow
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    fetchPulse();
  }, []);

  const fetchPulse = async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch("/api/pulse");
      const data = await res.json();
      if (data.pulse) {
        setPulse(data.pulse);
        setFilename(data.filename);
      }
    } catch (e) {
      console.error("Failed to fetch pulse", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  const runPipeline = async (sendEmail: boolean) => {
    setIsLoading(true);
    setShowResults(true); // reveal the bottom section immediately
    setLogs(`Starting pipeline (Weeks: ${weeks}, Send: ${sendEmail}, Email: ${email || "default"}, Topics: ${topics || "all"})... this normally takes 30-60 seconds.\n`);
    try {
      const res = await fetch("/api/run-pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          send: sendEmail,
          weeks: parseInt(weeks, 10),
          email: email,
          topics: topics
        }),
      });
      const data = await res.json();

      setLogs(prev => prev + "\n" + (data.stdout || ""));
      if (data.stderr) setLogs(prev => prev + "\n[ERRORS]\n" + data.stderr);

      if (res.ok) {
        setLogs(prev => prev + "\n\n✅ Pipeline completed successfully!");
        fetchPulse(); // refresh the view
      } else {
        setLogs(prev => prev + `\n\n❌ Pipeline failed: ${data.message}`);
      }
    } catch (e: any) {
      setLogs(prev => prev + `\n\n❌ Request failed: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Ultra-simple markdown parser for the exact structure we expect
  const renderMarkdown = (md: string) => {
    return md.split(/\r?\n/).map((line, i) => {
      // Headings
      if (line.startsWith("# ")) return <h1 key={i} className="text-3xl font-bold text-md-onSurface border-b border-md-outlineVariant pb-2 mb-4 mt-8">{line.slice(2)}</h1>;
      if (line.startsWith("## ")) return <h2 key={i} className="text-xl font-bold text-md-onSurface mt-6 mb-3">{line.slice(3)}</h2>;

      // Quotes (Material 3 standard secondary container feel)
      if (line.startsWith("> ")) return <blockquote key={i} className="pl-4 py-2 my-3 border-l-4 border-md-primary bg-md-secondaryContainer text-md-onSecondaryContainer italic rounded-r-md">{line.slice(2)}</blockquote>;

      // Lists (roughly)
      if (line.match(/^\\d+\\.\\s/)) {
        const text = line.replace(/^\\d+\\.\\s+/, "");
        // Bold parsing (simple)
        const parts = text.split(/\\*\\*(.*?)\\*\\*/g);
        return (
          <li key={i} className="mb-2 ml-4 list-decimal">
            {parts.map((p, j) => j % 2 === 1 ? <strong key={j} className="text-md-onSurface font-semibold">{p}</strong> : p)}
          </li>
        );
      }

      // Empty lines
      if (!line.trim()) return <br key={i} />;

      // Normal paragraphs
      return <p key={i} className="mb-2">{line}</p>;
    });
  };

  return (
    <div className="min-h-screen bg-md-surface p-8 font-[family-name:var(--font-geist-sans)]">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header & Controls (M3 Elevated Card) */}
        <div className="bg-md-surfaceContainer md-elevation-1 p-6 rounded-md-2xl border-none">
          <div className="mb-8 border-b border-md-outlineVariant pb-4">
            <h1 className="text-2xl font-bold text-md-onSurface">Groww Pulse Analyser</h1>
            <p className="text-md-onSurfaceVariant text-sm mt-1">AI-powered weekly review insights</p>
          </div>

          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs font-semibold text-md-onSurfaceVariant mb-1">Time Window (Weeks)</label>
              <input
                type="number"
                value={weeks}
                onChange={e => setWeeks(e.target.value)}
                className="w-full px-4 py-3 bg-md-surface border border-md-outline text-md-onSurface rounded-md-sm outline-none focus:border-2 focus:border-md-primary transition-all text-sm"
                min="1" max="52"
              />
            </div>
            <div className="flex-[2] min-w-[300px]">
              <label className="block text-xs font-semibold text-md-onSurfaceVariant mb-1">Recipient email ID</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="please enter your email"
                className="w-full px-4 py-3 bg-md-surface border border-md-outline text-md-onSurface rounded-md-sm outline-none focus:border-2 focus:border-md-primary transition-all text-sm"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-4 items-end mt-4">
            <div className="flex-1 min-w-[300px]">
              <label className="block text-xs font-semibold text-md-onSurfaceVariant mb-1">Topics to display (Comma-separated, optional)</label>
              <input
                type="text"
                value={topics}
                onChange={e => setTopics(e.target.value)}
                placeholder="e.g. Navigation, Trading Issues, UI..."
                className="w-full px-4 py-3 bg-md-surface border border-md-outline text-md-onSurface rounded-md-sm outline-none focus:border-2 focus:border-md-primary transition-all text-sm"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-4 mt-8 justify-end">
          <button
            onClick={() => runPipeline(false)}
            disabled={isLoading}
            className="px-6 py-3 border border-md-outline text-md-primary rounded-full text-sm font-medium hover:bg-md-surfaceVariant disabled:opacity-50 transition-colors"
          >
            {isLoading ? "Searching..." : "Search (Dry Run)"}
          </button>
          <button
            onClick={() => runPipeline(true)}
            disabled={isLoading}
            className="px-6 py-3 bg-md-primary text-md-onPrimary rounded-full text-sm font-medium hover:opacity-90 md-elevation-1 disabled:opacity-50 transition-colors"
          >
            Search & Send Email
          </button>
        </div>
      </div>

      {/* content area - ONLY VISIBLE IF showResults IS TRUE */}
      {showResults && (
        <div className="grid grid-cols-1 gap-6">
          {/* Output Card */}
          <div className="bg-md-surface md-elevation-1 p-8 rounded-md-2xl min-h-[500px]">
            {isRefreshing && !pulse ? (
              <div className="flex justify-center items-center h-full text-md-onSurfaceVariant">Loading latest pulse...</div>
            ) : pulse ? (
              <div>
                <div className="prose prose-p:text-md-onSurfaceVariant max-w-none">
                  {renderMarkdown(pulse)}
                </div>
              </div>
            ) : (
              <div className="flex justify-center items-center h-full text-md-onSurfaceVariant">
                No pulse notes generated yet. Run the pipeline!
              </div>
            )}
          </div>

          {/* Logs panel */}
          {logs && (
            <div className="bg-gray-900 rounded-xl p-4 md-elevation-1">
              <h3 className="text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider">Pipeline Logs</h3>
              <pre className="text-emerald-400 text-xs font-mono overflow-auto max-h-64 whitespace-pre-wrap">
                {logs}
              </pre>
            </div>
          )}

          {/* Back Button */}
          <div className="flex justify-center mt-4">
            <button
              onClick={() => setShowResults(false)}
              className="px-6 py-2.5 border border-md-outline bg-md-surface text-md-primary rounded-full text-sm font-medium hover:bg-md-surfaceVariant transition-colors md-elevation-1"
            >
              ← Back to Search
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
