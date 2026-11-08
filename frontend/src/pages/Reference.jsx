import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const SYSCALLS = [
  {
    name: "send(target, body) — MsgSend",
    http: "POST /kernel/send",
    desc: "Deliver a message to an agent thread. The caller becomes SEND-blocked until the target receives it, then REPLY-blocked until the target replies. From the browser, the HTTP request itself blocks.",
  },
  {
    name: "receive() — MsgReceive",
    http: "(agent-side syscall)",
    desc: "An agent waits for the next message in its mailbox. With an empty mailbox the agent is RECEIVE-blocked — the idle state of every server agent.",
  },
  {
    name: "reply(msg, body) — MsgReply",
    http: "(agent-side syscall)",
    desc: "Answer a received message. The blocked sender wakes up with the reply body and returns to RUNNING.",
  },
  {
    name: "chat router",
    http: "POST /kernel/chats",
    desc: "Open-or-continue: if a new message reads like a continuation of an existing chat thread, it routes there; otherwise the kernel spawns a fresh chat thread. Each chat is a thread that blocks on the agents it calls.",
  },
  {
    name: "send_async(target, body)",
    http: "POST /kernel/send_async → GET /kernel/messages/{id}",
    desc: "Browser-side convenience: enqueue a send and poll the message, so the UI can watch threads block each other mid-flight.",
  },
  {
    name: "thread table",
    http: "GET /kernel/agents",
    desc: "Every thread's state, who it's blocked on, and its mailbox depth (QNX pidin).",
  },
  {
    name: "event journal",
    http: "GET /kernel/events",
    desc: "Spawns, state transitions, message lifecycle (QNX sloginfo).",
  },
];

const STATES = [
  ["READY", "spawned, waiting for its first schedule"],
  ["RUNNING", "executing its own logic"],
  ["RECEIVE-BLOCKED", "in receive(), mailbox empty — the idle server state"],
  ["SEND-BLOCKED", "in send(), the target hasn't received the message yet"],
  ["REPLY-BLOCKED", "the target received the message and is working; sender waits for reply"],
  ["DEAD", "run() returned or crashed"],
];

function SyscallsSection() {
  return SYSCALLS.map((s) => (
    <div key={s.name} className="glass glass-panel" style={{ marginBottom: "0.75rem" }}>
      <strong>{s.name}</strong>
      <div style={{ fontFamily: "monospace", fontSize: "0.8rem", opacity: 0.8 }}>{s.http}</div>
      <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>{s.desc}</p>
    </div>
  ));
}

function StatesSection() {
  return (
    <div className="glass glass-panel">
      {STATES.map(([state, desc]) => (
        <div key={state} className="history-item">
          <strong style={{ fontFamily: "monospace" }}>{state}</strong> — {desc}
        </div>
      ))}
    </div>
  );
}

function CardsSection() {
  const [cards, setCards] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/kernel/agents");
        if (!res.ok) return;
        const { agents } = await res.json();
        const services = agents.filter((a) => a.kind !== "chat");
        const fetched = await Promise.all(
          services.map(async (a) => {
            const c = await fetch(`/.well-known/${a.name}-agent-card.json`);
            return c.ok ? c.json() : null;
          })
        );
        setCards(fetched.filter(Boolean));
      } catch {
        /* kernel offline */
      }
    })();
  }, []);

  return (
    <>
      <p className="page__lead">
        A2A discovery: each system agent publishes a card at
        <code> /.well-known/&#123;name&#125;-agent-card.json</code>.
      </p>
      {cards.map((card) => (
        <div key={card.name} className="glass glass-panel" style={{ marginBottom: "0.75rem" }}>
          <strong>{card.name}</strong>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.75rem" }}>
            {JSON.stringify(card, null, 2)}
          </pre>
        </div>
      ))}
    </>
  );
}

export default function Reference() {
  const { part } = useParams();

  return (
    <div className="page fade-in">
      <h1 className="page__title">
        {part === "states" ? "Thread states" : part === "cards" ? "Agent cards" : "Syscalls"}
      </h1>
      {part === "states" && <StatesSection />}
      {part === "cards" && <CardsSection />}
      {part !== "states" && part !== "cards" && <SyscallsSection />}
    </div>
  );
}
