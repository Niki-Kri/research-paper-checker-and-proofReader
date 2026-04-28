


import { useState } from "react";
import axios from "axios";
import {
  UploadCloud,
  FileText,
  CheckCircle,
  AlertTriangle,
  Download,
  BookOpen,
  PenTool,
  BarChart3,
  Quote,
  Sparkles,
} from "lucide-react";
import "./App.css";

const API_URL = "http://127.0.0.1:5000";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please upload a PDF file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);

      const res = await axios.post(`${API_URL}/check`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setResult(res.data);
    } catch (error) {
      console.error(error);
      alert("Something went wrong while analyzing the paper.");
    } finally {
      setLoading(false);
    }
  };

  const downloadPDF = () => {
    window.open(`${API_URL}/download`, "_blank");
  };

  return (
    <div className="app">
      <div className="bg-blur blur-one"></div>
      <div className="bg-blur blur-two"></div>

      <nav className="navbar">
        <div className="logo">
          <Sparkles size={24} />
          <span>PaperLens AI</span>
        </div>

      </nav>

      <section className="hero">
        <div className="hero-content">
          <p className="eyebrow">AI Powered Academic Audit System</p>
          <h1>Research Paper Format Checker & Proofreader</h1>
          <p className="hero-text">
            Upload your research paper and instantly analyze formatting, grammar, readability, citations, and academic tone — aligned with top publishing standards like IEEE, Springer, and Elsevier.
          </p>

          <div className="format-tags">
            <span>Format Check</span>
            <span>Grammar</span>
            <span>Citations</span>
            <span>Readability</span>
            <span>Compliance</span>
          </div>
        </div>

        <div className="upload-card">
          <div className="upload-icon">
            <UploadCloud size={44} />
          </div>

          <h2>Upload Research Paper</h2>
          <p>Only PDF files are supported</p>

          <label className="file-box">
            <input type="file" accept="application/pdf" onChange={handleFileChange} />
            <FileText size={30} />
            <span>{file ? file.name : "Choose or drag your PDF here"}</span>
          </label>

          <button onClick={handleUpload} disabled={loading} className="analyze-btn">
            {loading ? "Analyzing Paper..." : "Analyze Paper"}
          </button>
        </div>
      </section>

      {result && (
        <main className="dashboard">
          <section className="paper-header glass-card">
            <div>
              <p className="section-label">Detected Paper</p>
              <h2>{result.title}</h2>
              <p>{result.description}</p>
            </div>

            <div className="publisher-box">
              <span>Best Matched Format</span>
              <h3>{result.publisher}</h3>
            </div>
          </section>

          <section className="summary-grid">
            <SummaryCard
              icon={<FileText />}
              title="Word Count"
              value={result.summary?.word_count}
              type="blue"
            />
            <SummaryCard
              icon={<PenTool />}
              title="Writing Issues"
              value={result.summary?.grammar_issues}
              type="orange"
            />
            <SummaryCard
              icon={<Quote />}
              title="Citations"
              value={result.summary?.citations}
              type="green"
            />
            <SummaryCard
              icon={<AlertTriangle />}
              title="Formatting Issues"
              value={result.summary?.formatting_issues}
              type="red"
            />
          </section>

          <section className="glass-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Publisher Compliance</p>
                <h2>Format Matching Score</h2>
              </div>
              <BarChart3 />
            </div>

            <div className="format-score-grid">
              {Object.entries(result.formatting_analysis || {}).map(([format, data]) => (
                <FormatScore key={format} format={format} data={data} />
              ))}
            </div>
          </section>

          <section className="two-column">
            <CitationCard citation={result.citation_analysis} />

            <ReadabilityTone
              readability={result.readability_analysis}
              tone={result.tone_analysis}
            />
          </section>

          <section className="glass-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Proofreading Report</p>
                <h2>Writing, Grammar & Tone Issues</h2>
              </div>

              <button className="download-btn" onClick={downloadPDF}>
                <Download size={18} />
                Download Highlighted PDF
              </button>
            </div>

            <IssueTable issues={result.writing_issues || []} />
          </section>

          <section className="glass-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Formatting Audit</p>
                <h2>Detailed Formatting Issues</h2>
              </div>
            </div>

            <FormattingIssues issues={result.all_formatting_issues || []} />
          </section>
        </main>
      )}
    </div>
  );
}

function SummaryCard({ icon, title, value, type }) {
  return (
    <div className={`summary-card ${type}`}>
      <div className="summary-icon">{icon}</div>
      <p>{title}</p>
      <h2>{value ?? 0}</h2>
    </div>
  );
}

function FormatScore({ format, data }) {
  const score = Number(data?.score || 0);
  const percentage = Math.min(score * 10, 100);

  return (
    <div className="format-card">
      <div
        className="circle"
        style={{
          background: `conic-gradient(#22d3ee ${percentage}%, rgba(255,255,255,0.12) 0)`,
        }}
      >
        <div className="circle-inner">
          <strong>{score}</strong>
          <span>/10</span>
        </div>
      </div>

      <h3>{format}</h3>

      <div className="section-status">
        {Object.entries(data?.sections || {}).map(([sec, status]) => (
          <span
            key={sec}
            className={status === "Found" ? "found" : "missing"}
          >
            {status === "Found" ? "✓" : "×"} {sec}
          </span>
        ))}
      </div>
    </div>
  );
}

function CitationCard({ citation }) {
  return (
    <section className="glass-card">
      <div className="section-heading">
        <div>
          <p className="section-label">Citation Check</p>
          <h2>Citation Analysis</h2>
        </div>
        <BookOpen />
      </div>

      <div className="info-list">
        <div>
          <span>Detected Style</span>
          <strong>{citation?.detected_style || "Unknown"}</strong>
        </div>

        <div>
          <span>Total Citations</span>
          <strong>{citation?.count || 0}</strong>
        </div>

        <div>
          <span>Status</span>
          <strong className={citation?.valid ? "success-text" : "danger-text"}>
            {citation?.status}
          </strong>
        </div>
      </div>

      {citation?.issues?.length > 0 && (
        <ul className="suggestion-list">
          {citation.issues.map((issue, index) => (
            <li key={index}>{issue}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReadabilityTone({ readability, tone }) {
  return (
    <section className="glass-card">
      <div className="section-heading">
        <div>
          <p className="section-label">Academic Quality</p>
          <h2>Readability & Tone</h2>
        </div>
        <CheckCircle />
      </div>

      <div className="quality-grid">
        <div>
          <span>Readability Score</span>
          <strong>{readability?.score}</strong>
        </div>

        <div>
          <span>Grade Level</span>
          <strong>{readability?.grade}</strong>
        </div>

        <div>
          <span>Tone Score</span>
          <strong>{tone?.score}/10</strong>
        </div>
      </div>

      <ul className="suggestion-list">
        {[...(readability?.suggestions || []), ...(tone?.suggestions || [])].map(
          (s, index) => (
            <li key={index}>{s}</li>
          )
        )}
      </ul>
    </section>
  );
}

function IssueTable({ issues }) {
  if (issues.length === 0) {
    return <p className="empty-msg">No writing issues found.</p>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Error Text</th>
            <th>Message</th>
            <th>Sentence</th>
            <th>Suggestions</th>
            <th>Severity</th>
          </tr>
        </thead>

        <tbody>
          {issues.slice(0, 40).map((issue, index) => (
            <tr key={index}>
              <td>{issue.error_text || issue.type || "Issue"}</td>
              <td>{issue.message}</td>
              <td>{issue.sentence || "-"}</td>
              <td>
                {Array.isArray(issue.suggestions) && issue.suggestions.length > 0
                  ? issue.suggestions.join(", ")
                  : "-"}
              </td>
              <td>
                <span className={`severity ${(issue.severity || "medium").toLowerCase()}`}>
                  {issue.severity || issue.rule || "Medium"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FormattingIssues({ issues }) {
  if (issues.length === 0) {
    return <p className="empty-msg">No formatting issues found.</p>;
  }

  return (
    <div className="issue-grid">
      {issues.slice(0, 30).map((issue, index) => (
        <div className="format-issue" key={index}>
          <AlertTriangle size={20} />
          <div>
            <h4>{issue.type || "Formatting Issue"}</h4>
            <p>
              {issue.message ||
                issue.text ||
                issue.found ||
                JSON.stringify(issue)}
            </p>
            {issue.page && <span>Page {issue.page}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default App;