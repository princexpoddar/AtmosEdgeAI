import { useState, useEffect, useRef } from "react";
import { useStations } from "@/hooks/useStations";
import { askCitizenAI, getRegionalAdvisory } from "@/services/api";
import Navbar from "@/components/layout/Navbar";
import Spinner from "@/components/ui/Spinner";

const LANGUAGES = [
  { code: "en", label: "🌐 English", flag: "🌐" },
  { code: "kn", label: "💛 ಕನ್ನಡ (Kannada)", flag: "💛" },
  { code: "ta", label: "❤️ தமிழ் (Tamil)", flag: "❤️" },
  { code: "hi", label: "🧡 हिंदी (Hindi)", flag: "🧡" },
  { code: "mr", label: "💙 मराठी (Marathi)", flag: "💙" },
  { code: "bn", label: "💚 বাংলা (Bengali)", flag: "💚" },
];

const PROMPT_CHIPS = [
  { text: "Can I go for an outdoor morning run or exercise today?", icon: "🏃" },
  { text: "Is it safe for young children and senior citizens outside?", icon: "👶" },
  { text: "Do I need to wear an N95 mask for my commute?", icon: "😷" },
  { text: "What health precautions should asthmatic patients take?", icon: "🫁" },
  { text: "Are outdoor construction workers safe in this area?", icon: "🏗️" },
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
        // Welcome message in initial chat
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

  // Scroll to bottom of chat
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
          text: "⚠️ Sorry, I could not process your query at this moment. Please check server connections.",
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
      <div className="enforcement-page">

        {/* Header Title & Controls */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "var(--text-1)" }}>
              🗣️ Citizen Health Risk Advisory System (Multi-Lingual AI)
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-2)", margin: "2px 0 0 0" }}>
              Real-Time AI Telemetry Health Advisor — Powered by Google Gemini 2.5 Flash
            </p>
          </div>

          {/* Station & Language Controls */}
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={selectedStationId}
              onChange={(e) => setSelectedStationId(e.target.value)}
              disabled={stationsLoading}
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                padding: "8px 14px",
                borderRadius: 8,
                fontSize: 13,
                outline: "none",
                cursor: "pointer"
              }}
            >
              {stations.map((st) => (
                <option key={st.id} value={st.id}>
                  📍 {st.name} ({st.city}) — AQI {st.aqi ?? "N/A"}
                </option>
              ))}
            </select>

            <select
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                padding: "8px 14px",
                borderRadius: 8,
                fontSize: 13,
                outline: "none",
                cursor: "pointer"
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Station Real-Time Health Risk Header Dossier */}
        {stationAdvisory && selectedStation && (
          <div className="card" style={{ padding: 16, marginBottom: 16, background: "rgba(30, 41, 59, 0.7)", border: "1px solid rgba(59, 130, 246, 0.3)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
              <div>
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1, color: "#60a5fa" }}>
                  MONITORING CATCHMENT HEALTH PROFILE
                </span>
                <h3 style={{ fontSize: 18, fontWeight: 700, margin: "4px 0", color: "#f8fafc" }}>
                  📍 {stationAdvisory.station_name} ({stationAdvisory.city}, {stationAdvisory.state})
                </h3>
                <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
                  <span className="badge badge-outline" style={{ borderColor: stationAdvisory.category === "Good" ? "#22c55e" : "#ef4444", color: "#f8fafc" }}>
                    AQI Status: {stationAdvisory.category} (PM2.5: {stationAdvisory.pm25} µg/m³)
                  </span>
                  <span className="badge badge-outline" style={{ borderColor: "#a855f7", color: "#c084fc" }}>
                    ⚖️ {stationAdvisory.spcb_authority}
                  </span>
                </div>
              </div>

              {/* Receptor Summary Pills */}
              <div style={{ display: "flex", gap: 12, alignItems: "center", background: "rgba(15, 23, 42, 0.6)", padding: "10px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)" }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#f8fafc" }}>{stationAdvisory.sensitive_receptors_summary}</div>
                  <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>Vulnerability Level: <span style={{ color: "#f87171", fontWeight: 700 }}>{stationAdvisory.vulnerability_level}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Suggested Prompt Chips */}
        <div style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", display: "block", marginBottom: 8 }}>
            💡 QUICK HEALTH QUESTIONS (CLICK TO ASK GEMINI AI):
          </span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {PROMPT_CHIPS.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip.text)}
                disabled={asking}
                style={{
                  background: "rgba(30, 41, 59, 0.8)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  color: "#cbd5e1",
                  padding: "6px 12px",
                  borderRadius: 20,
                  fontSize: 12,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  transition: "all 0.2s ease"
                }}
              >
                <span>{chip.icon}</span>
                <span>{chip.text}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Main Interactive AI Conversational Log */}
        <div className="card" style={{ padding: 16, minHeight: 380, display: "flex", flexDirection: "column", background: "rgba(15, 23, 42, 0.85)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 10, borderBottom: "1px solid rgba(255,255,255,0.08)", marginBottom: 14 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#60a5fa" }}>
              🤖 Gemini 2.5 Flash Air Safety Assistant ({LANGUAGES.find(l => l.code === selectedLang)?.label})
            </span>
            <span style={{ fontSize: 11, color: "#34d399" }}>● Connected to Live CAAQMS Telemetry</span>
          </div>

          {/* Chat Messages */}
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, paddingRight: 4, maxHeight: 420 }}>
            {chatLog.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "80%",
                    background: msg.sender === "user" ? "#2563eb" : "rgba(30, 41, 59, 0.9)",
                    border: msg.sender === "user" ? "none" : "1px solid rgba(59, 130, 246, 0.3)",
                    color: "#f8fafc",
                    padding: "12px 16px",
                    borderRadius: msg.sender === "user" ? "16px 16px 2px 16px" : "16px 16px 16px 2px",
                    fontSize: 14,
                    lineHeight: 1.5,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
                  }}
                >
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.text}</p>
                  {msg.english && (
                    <p style={{ fontSize: 11, color: "#94a3b8", margin: "6px 0 0 0", fontStyle: "italic", borderTop: "1px dashed rgba(255,255,255,0.1)", paddingTop: 4 }}>
                      English: {msg.english}
                    </p>
                  )}
                </div>
                <div style={{ fontSize: 10, color: "#64748b", marginTop: 4, padding: "0 4px" }}>
                  {msg.sender === "user" ? "You" : `🤖 Gemini 2.5 Flash • ${msg.time}`}
                </div>
              </div>
            ))}

            {asking && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#60a5fa", fontSize: 13 }}>
                <Spinner size="sm" />
                <span>Gemini AI is analyzing station telemetry &amp; generating native health advice…</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input Box */}
          <div style={{ display: "flex", gap: 10, marginTop: 16, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder={`Ask Gemini AI any health or air safety question in ${LANGUAGES.find(l => l.code === selectedLang)?.label}…`}
              disabled={asking}
              style={{
                flex: 1,
                background: "rgba(30, 41, 59, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                padding: "10px 14px",
                borderRadius: 8,
                fontSize: 13,
                outline: "none"
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={asking || !inputQuery.trim()}
              className="btn btn-primary"
              style={{ padding: "0 20px" }}
            >
              {asking ? "Thinking…" : "Ask AI 🚀"}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
