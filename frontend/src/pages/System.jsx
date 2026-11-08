import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const STATUS_COLORS = {
  pending: "#f97316",
  received: "#facc15",
  replied: "#4ade80",
  failed: "#ef4444",
};

function ChannelsSection() {
  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/kernel/messages");
        if (res.ok) setMessages((await res.json()).messages);
      } catch {
        /* kernel offline */
      }
    };
    poll();
    const id = setInterval(poll, 500);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      <p className="page__lead">
        Every A2A exchange is one synchronous message: send → receive → reply. Newest first; click
        to inspect.
      </p>
      <div className="glass glass-panel glass-panel--scroll" style={{ fontFamily: "monospace" }}>
        {messages.length === 0 && <div className="history-item">no IPC messages yet</div>}
        {messages.map((m) => (
          <div
            key={m.msg_id}
            className="history-item"
            style={{ cursor: "pointer" }}
            onClick={() => setSelected(selected?.msg_id === m.msg_id ? null : m)}
          >
            #{String(m.msg_id).padEnd(4)} {m.sender} → {m.target}{" "}
            <span style={{ color: STATUS_COLORS[m.status] || "inherit" }}>[{m.status}]</span>
            {m.error ? ` — ${m.error}` : ""}
          </div>
        ))}
      </div>
      {selected && (
        <div className="glass glass-panel" style={{ marginTop: "0.75rem" }}>
          <strong>
            #{selected.msg_id}: {selected.sender} → {selected.target}
          </strong>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>
            {JSON.stringify({ body: selected.body, reply: selected.reply }, null, 2)}
          </pre>
        </div>
      )}
    </>
  );
}

function LogSection() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/kernel/events");
        if (res.ok) setEvents((await res.json()).events.slice().reverse());
      } catch {
        /* kernel offline */
      }
    };
    poll();
    const id = setInterval(poll, 500);
    return () => clearInterval(id);
  }, []);

  return (
    <>
      <p className="page__lead">
        The kernel&apos;s event journal (QNX <code>sloginfo</code>): spawns, state transitions, and
        every message in flight.
      </p>
      <div className="glass glass-panel glass-panel--scroll" style={{ fontFamily: "monospace" }}>
        {events.length === 0 && <div className="history-item">log empty — kernel may be offline</div>}
        {events.map((e, i) => (
          <div key={i} className="history-item">
            [{e.ts?.slice(11, 19)}] {e.type} {e.agent || ""}
            {e.peer ? ` ↔ ${e.peer}` : ""}
            {e.msg_id ? ` #${e.msg_id}` : ""}
            {e.state ? ` → ${e.state}` : ""}
            {e.waiting_on ? ` (waiting on ${e.waiting_on})` : ""}
            {e.detail ? ` — ${e.detail}` : ""}
          </div>
        ))}
      </div>
    </>
  );
}

export default function System() {
  const { part } = useParams();

  return (
    <div className="page fade-in">
      <h1 className="page__title">{part === "log" ? "System log" : "Channels"}</h1>
      {part === "log" ? <LogSection /> : <ChannelsSection />}
    </div>
  );
}
