import { useState, useEffect, useRef } from "react";
import { useStations } from "@/hooks/useStations";
import { askCitizenAI, getRegionalAdvisory } from "@/services/api";
import Navbar from "@/components/layout/Navbar";
import Spinner from "@/components/ui/Spinner";
import { Send, Bot } from "lucide-react";

const LANGUAGES = [
  { code: "en", label: "English", icon: "🌐" },
  { code: "kn", label: "ಕನ್ನಡ", icon: "💛" },
  { code: "ta", label: "தமிழ்", icon: "❤️" },
  { code: "hi", label: "हिंदी", icon: "🧡" },
  { code: "mr", label: "मराठी", icon: "💙" },
  { code: "bn", label: "বাংলা", icon: "💚" },
];

const PROMPT_CHIPS = [
  { text: "Can I go for an outdoor morning run today?", icon: "🏃" },
  { text: "Is it safe for young children and elderly outside?", icon: "👶" },
  { text: "Do I need to wear an N95 mask for my commute?", icon: "😷" },
  { text: "What health precautions should asthma patients take?", icon: "🫁" },
];

export default function CitizenAdvisory() {
  const { stations, loading: stationsLoading } = useStations();
  const [selectedStationId, setSelectedStationId] = useState("");
  const [selectedLang, setSelectedLang] = useState("en");
  const [stationAdvisory, setStationAdvisory] = useState(null);
  const [inputQuery, setInputQuery] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [asking, setAsking] = useState(false);
  const chatEndRef = useRef(null);

  // Set default station
  useEffect(() => {
    if (stations.length > 0 && !selectedStationId) {
      setSelectedStationId(stations[0].id);
    }
  }, [stations, selectedStationId]);

  // Load station health advisory overview
  useEffect(() => {
    if (!selectedStationId) return;
    getRegionalAdvisory(selectedStationId, selectedLang)
      .then((res) => {
        setStationAdvisory(res);
        setChatLog([
          {
            sender: "ai",
            text: res.advisory_message_regional,
            english: res.advisory_message_english,
            model: "Gemini 2.5 Flash",
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      })
      .catch((err) => console.error("Advisory error:", err));
  }, [selectedStationId, selectedLang]);

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, asking]);

  const handleSend = async (queryText) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || !selectedStationId || asking) return;

    const userMsg = {
      sender: "user",
      text: textToSend,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setChatLog((prev) => [...prev, userMsg]);
    if (!queryText) setInputQuery("");
    setAsking(true);

    try {
      const res = await askCitizenAI({
        stationId: selectedStationId,
        query: textToSend,
        lang: selectedLang,
      });

      const aiMsg = {
        sender: "ai",
        text: res.reply,
        model: res.model_used || "Gemini 2.5 Flash",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setChatLog((prev) => [...prev, aiMsg]);
    } catch (_err) {
      setChatLog((prev) => [
        ...prev,
        {
          sender: "ai",
          text: "⚠️ Unable to reach Gemini AI engine. Please verify server connectivity.",
          model: "Error",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  const selectedStation = stations.find((s) => s.id === selectedStationId);

  return (
    <div className="app-root">
      <Navbar />
      <div className="citizen-advisory-page">

        {/* Page Title Header */}
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "var(--text-1)" }}>
            🗣️ Citizen Health Risk Advisory System
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-2)", margin: "3px 0 0 0" }}>
            Real-Time Multi-Lingual Citizen Environmental Health Advisor — Powered by Google Gemini 2.5 Flash
          </p>
        </div>

        {/* Two-Column Grid */}
        <div className="citizen-advisory-grid">

          {/* Left Sidebar */}
          <div className="citizen-sidebar">

            {/* Station Selector Card */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 10 }}>Select Station Catchment</h4>
              <select
                className="chat-input-field"
                value={selectedStationId}
                onChange={(e) => setSelectedStationId(e.target.value)}
                disabled={stationsLoading}
                style={{ width: "100%", cursor: "pointer" }}
              >
                {stations.map((st) => (
                  <option key={st.id} value={st.id}>
                    📍 {st.name} ({st.city})
                  </option>
                ))}
              </select>
            </div>

            {/* Catchment Health Profile Card */}
            {stationAdvisory && selectedStation && (
              <div className="card" style={{ padding: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <div>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", textTransform: "uppercase", letterSpacing: 0.5 }}>
                      CATCHMENT PROFILE
                    </span>
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: "2px 0 0 0", color: "var(--text-1)" }}>
                      {stationAdvisory.station_name}
                    </h3>
                    <span style={{ fontSize: 12, color: "var(--text-3)" }}>
                      {stationAdvisory.city}, {stationAdvisory.state}
                    </span>
                  </div>
                  <span
                    className="badge"
                    style={{
                      background: stationAdvisory.category === "Good" ? "var(--green-dim)" : "var(--red-dim)",
                      color: stationAdvisory.category === "Good" ? "var(--green)" : "var(--red)",
                      borderColor: stationAdvisory.category === "Good" ? "var(--green)" : "var(--red)",
                    }}
                  >
                    {stationAdvisory.category}
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12, fontSize: 12, color: "var(--text-2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border-soft)" }}>
                    <span>PM2.5 / NO2</span>
                    <strong style={{ color: "var(--text-1)" }}>{stationAdvisory.pm25} / {stationAdvisory.no2} µg/m³</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border-soft)" }}>
                    <span>SPCB Jurisdiction</span>
                    <strong style={{ color: "var(--purple)" }}>{stationAdvisory.spcb_authority}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                    <span>Sensitive Receptors</span>
                    <strong style={{ color: "var(--text-1)" }}>{stationAdvisory.sensitive_receptors_summary?.split("located")[0]}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Native Language Selector Card */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 10 }}>Native Regional Language</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
                {LANGUAGES.map((l) => {
                  const isSel = selectedLang === l.code;
                  return (
                    <button
                      key={l.code}
                      onClick={() => setSelectedLang(l.code)}
                      className={`btn ${isSel ? "btn-primary" : "btn-secondary"} btn-sm`}
                      style={{ justifyContent: "center" }}
                    >
                      <span>{l.icon}</span>
                      <span>{l.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Suggested Quick Prompts Card */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 10 }}>Quick Health Doubts</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {PROMPT_CHIPS.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(chip.text)}
                    disabled={asking}
                    className="prompt-chip-btn"
                    style={{ textAlign: "left", width: "100%" }}
                  >
                    <span>{chip.icon}</span>
                    <span>{chip.text}</span>
                  </button>
                ))}
              </div>
            </div>

          </div>

          {/* Right Main Chat Terminal */}
          <div className="citizen-chat-terminal">

            {/* Chat Terminal Header */}
            <div className="chat-terminal-header">
              <div className="chat-terminal-title">
                <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--accent-dim)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Bot size={16} />
                </div>
                <div>
                  <span style={{ fontWeight: 600, color: "var(--text-1)" }}>Gemini 2.5 Flash Health Assistant</span>
                  <div style={{ fontSize: 11, color: "var(--text-3)", display: "flex", alignItems: "center", gap: 6, marginTop: 1 }}>
                    <span className="live-pulse" />
                    <span>Real-Time CAAQMS Telemetry Linked</span>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className="badge badge-outline" style={{ color: "var(--accent)", borderColor: "var(--accent)" }}>
                  {LANGUAGES.find((l) => l.code === selectedLang)?.label} Script
                </span>
              </div>
            </div>

            {/* Scrollable Chat Message Stream */}
            <div className="chat-log-container">
              {chatLog.map((msg, i) => (
                <div key={i} className={`chat-bubble-row ${msg.sender}`}>
                  <div className={`chat-bubble ${msg.sender}`}>
                    <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.text}</p>
                    {msg.english && (
                      <p style={{ fontSize: 11, color: "var(--text-3)", margin: "6px 0 0 0", fontStyle: "italic", borderTop: "1px dashed var(--border)", paddingTop: 4 }}>
                        Translation: {msg.english}
                      </p>
                    )}
                  </div>
                  <div className="chat-bubble-meta">
                    {msg.sender === "user" ? "You" : `🤖 ${msg.model} • ${msg.time}`}
                  </div>
                </div>
              ))}

              {asking && (
                <div className="chat-bubble-row ai">
                  <div className="chat-bubble ai" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Spinner size="sm" />
                    <span style={{ fontSize: 12, color: "var(--text-2)" }}>
                      Gemini 2.5 Flash is analyzing live station telemetry &amp; generating health advice…
                    </span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input Bar */}
            <div className="chat-input-bar">
              <input
                type="text"
                className="chat-input-field"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={`Ask any health question in ${LANGUAGES.find((l) => l.code === selectedLang)?.label}…`}
                disabled={asking}
              />
              <button
                onClick={() => handleSend()}
                disabled={asking || !inputQuery.trim()}
                className="btn btn-primary"
              >
                <span>{asking ? "Analyzing…" : "Ask AI"}</span>
                <Send size={13} />
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
