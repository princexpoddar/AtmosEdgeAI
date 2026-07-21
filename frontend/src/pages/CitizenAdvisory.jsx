import { useState, useEffect, useRef, useCallback } from "react";
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
  { text: "What precautions for asthma patients today?", icon: "🫁" },
  { text: "Are outdoor construction workers safe here?", icon: "🏗️" },
  { text: "Is it safe to open windows at home?", icon: "🏠" },
];

function formatMessageText(text) {
  if (!text) return "";
  const lines = text.split("\n");
  return lines.map((line, lineIdx) => {
    // Process **bold** text in this line
    const parts = line.split("**");
    const formattedLine = parts.map((part, partIdx) => {
      if (partIdx % 2 === 1) {
        return <strong key={partIdx}>{part}</strong>;
      }
      return part;
    });

    // Check if the line is a list item starting with *, -, or •
    const listMatch = line.trim().match(/^([*-\u2022])\s+(.*)$/);
    if (listMatch) {
      const itemContent = listMatch[2];
      const itemParts = itemContent.split("**");
      const formattedContent = itemParts.map((p, idx) => {
        if (idx % 2 === 1) {
          return <strong key={idx}>{p}</strong>;
        }
        return p;
      });
      return (
        <li key={lineIdx} style={{ marginLeft: 20, marginBottom: 4, listStyleType: "disc" }}>
          {formattedContent}
        </li>
      );
    }

    return (
      <div key={lineIdx} style={{ minHeight: "1.2em", marginBottom: 2 }}>
        {formattedLine}
      </div>
    );
  });
}

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

  // Load station profile (only on station change — NOT on language change)
  useEffect(() => {
    if (!selectedStationId) return;
    getRegionalAdvisory(selectedStationId, "en")
      .then((res) => {
        setStationAdvisory(res);
        // Only set the welcome message when the station changes (chat reset on station switch)
        setChatLog([
          {
            sender: "ai",
            text: res.advisory_message_english,
            model: "AtmosEdgeAI",
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      })
      .catch((err) => console.error("Advisory error:", err));
  }, [selectedStationId]); // ← Only station triggers reset, NOT language

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, asking]);

  const handleSend = useCallback(async (queryText) => {
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
      // Always pass the currently selected language to the AI
      const res = await askCitizenAI({
        stationId: selectedStationId,
        query: textToSend,
        lang: selectedLang,      // ← uses live selectedLang state at call time
      });

      const aiMsg = {
        sender: "ai",
        text: res.reply,
        model: res.model_used || "Gemini 2.5 Flash",
        lang: selectedLang,
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
  }, [inputQuery, selectedStationId, selectedLang, asking]);

  const selectedStation = stations.find((s) => s.id === selectedStationId);
  const activeLang = LANGUAGES.find((l) => l.code === selectedLang);

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

          {/* ── Left Sidebar ── */}
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
              <div className="card" style={{ padding: 16, flex: 1, display: "flex", flexDirection: "column" }}>
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
                      background: stationAdvisory.category === "Good" ? "var(--green-dim)" : stationAdvisory.category === "Satisfactory" ? "var(--yellow-dim)" : "var(--red-dim)",
                      color: stationAdvisory.category === "Good" ? "var(--green)" : stationAdvisory.category === "Satisfactory" ? "var(--yellow)" : "var(--red)",
                    }}
                  >
                    {stationAdvisory.category}
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: "var(--text-2)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border-soft)" }}>
                    <span>PM2.5</span>
                    <strong style={{ color: "var(--text-1)" }}>{stationAdvisory.pm25} µg/m³</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border-soft)" }}>
                    <span>NO2</span>
                    <strong style={{ color: "var(--text-1)" }}>{stationAdvisory.no2} µg/m³</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border-soft)" }}>
                    <span>SPCB</span>
                    <strong style={{ color: "var(--purple)", fontSize: 11 }}>{stationAdvisory.spcb_authority}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0" }}>
                    <span>Vulnerability</span>
                    <strong style={{ color: "var(--text-1)" }}>{stationAdvisory.vulnerability_level}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Native Language Selector Card */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 4 }}>AI Response Language</h4>
              <p style={{ fontSize: 11, color: "var(--text-3)", margin: "0 0 10px 0" }}>
                Gemini AI will reply in the selected native script
              </p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}>
                {LANGUAGES.map((l) => {
                  const isSel = selectedLang === l.code;
                  return (
                    <button
                      key={l.code}
                      onClick={() => setSelectedLang(l.code)}
                      className={`btn ${isSel ? "btn-primary" : "btn-secondary"} btn-sm`}
                      style={{ justifyContent: "center", gap: 6 }}
                    >
                      <span>{l.icon}</span>
                      <span>{l.label}</span>
                    </button>
                  );
                })}
              </div>
              {selectedLang !== "en" && (
                <p style={{ fontSize: 11, color: "var(--accent)", margin: "10px 0 0 0", background: "var(--accent-dim)", borderRadius: "var(--radius-sm)", padding: "6px 8px" }}>
                  ✓ AI will respond in {activeLang?.label} script for your next question
                </p>
              )}
            </div>

          </div>

          {/* ── Right Main Chat Terminal ── */}
          <div className="citizen-chat-terminal">

            {/* Chat Terminal Header */}
            <div className="chat-terminal-header">
              <div className="chat-terminal-title">
                <div style={{ width: 28, height: 28, borderRadius: "var(--radius-sm)", background: "var(--accent-dim)", color: "var(--accent)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
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
                  {activeLang?.icon} {activeLang?.label}
                </span>
              </div>
            </div>

            {/* Scrollable Chat Message Stream */}
            <div className="chat-log-container">
              {chatLog.map((msg, i) => (
                <div key={i} className={`chat-bubble-row ${msg.sender}`}>
                  <div className={`chat-bubble ${msg.sender}`}>
                    <div style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
                      {formatMessageText(msg.text)}
                    </div>
                  </div>
                  <div className="chat-bubble-meta">
                    {msg.sender === "user"
                      ? `You • ${msg.time}`
                      : `🤖 ${msg.model} • ${msg.time}${msg.lang && msg.lang !== "en" ? ` • ${LANGUAGES.find(l => l.code === msg.lang)?.label}` : ""}`}
                  </div>
                </div>
              ))}

              {asking && (
                <div className="chat-bubble-row ai">
                  <div className="chat-bubble ai" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Spinner size="sm" />
                    <span style={{ fontSize: 12, color: "var(--text-2)" }}>
                      Generating {activeLang?.label} health advice from live telemetry…
                    </span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* ── Recommendation Chips Bar (above input) ── */}
            <div style={{
              padding: "10px 20px 0 20px",
              borderTop: "1px solid var(--border-soft)",
              background: "var(--bg-2)",
            }}>
              <p style={{ fontSize: 11, color: "var(--text-3)", margin: "0 0 8px 0", fontWeight: 500 }}>
                SUGGESTED QUESTIONS
              </p>
              <div style={{
                display: "flex",
                gap: 8,
                overflowX: "auto",
                paddingBottom: 10,
                scrollbarWidth: "none",
              }}>
                {PROMPT_CHIPS.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(chip.text)}
                    disabled={asking}
                    className="prompt-chip-btn"
                    style={{ flexShrink: 0 }}
                  >
                    <span>{chip.icon}</span>
                    <span style={{ whiteSpace: "nowrap" }}>{chip.text}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Input Bar */}
            <div className="chat-input-bar">
              <input
                type="text"
                className="chat-input-field"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder={`Ask any health question${selectedLang !== "en" ? ` — AI replies in ${activeLang?.label}` : " in any language"}…`}
                disabled={asking}
              />
              <button
                onClick={() => handleSend()}
                disabled={asking || !inputQuery.trim()}
                className="btn btn-primary"
              >
                <span>{asking ? "Thinking…" : "Ask AI"}</span>
                <Send size={13} />
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
