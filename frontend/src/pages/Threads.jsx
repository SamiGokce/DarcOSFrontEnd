import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { listModels, listPersonas, modelStatus, speak } from "../api/forge";
import { blankPersona, historyFor } from "../persona/store";
import styles from "./Threads.module.css";

const SAMPLING_KEY = "basalisk.modelSampling";

function readSampling() {
  try {
    return JSON.parse(localStorage.getItem(SAMPLING_KEY) || "{}");
  } catch {
    return {};
  }
}

function personaBody(persona) {
  const body = { ...blankPersona(), ...persona };
  delete body.id;
  delete body.created_at;
  delete body.updated_at;
  return body;
}

function PygmalionChat() {
  const [params] = useSearchParams();
  const selectedId = params.get("model");
  const [persona, setPersona] = useState(null);
  const [turns, setTurns] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [model, setModel] = useState(null);
  const [chosen, setChosen] = useState(null);
  const [missing, setMissing] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    let stopped = false;
    listPersonas()
      .then((personas) => {
        if (stopped) return;
        const chosen = personas.find((item) => item.name === "Galatea") || personas[0];
        if (!chosen) {
          setMissing(true);
          return;
        }
        setPersona({ ...blankPersona(), ...chosen });
        setTurns(historyFor(chosen.id).slice());
      })
      .catch((err) => {
        if (!stopped) setNotice(err.message);
      });
    return () => {
      stopped = true;
    };
  }, []);

  useEffect(() => {
    let stopped = false;
    const read = () => {
      modelStatus()
        .then((status) => {
          if (!stopped) setModel(status);
        })
        .catch(() => {});
      listModels()
        .then((rows) => {
          if (stopped) return;
          const pick = rows.find((row) => String(row.id) === String(selectedId)) || rows.find((row) => row.state === "ready") || rows[0];
          setChosen(pick || null);
        })
        .catch(() => {});
    };
    read();
    const id = setInterval(read, 2500);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [selectedId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns.length, busy]);

  const send = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || !persona || busy) return;
    const history = historyFor(persona.id);
    history.push({ role: "you", content: text });
    setTurns(history.slice());
    setInput("");
    setBusy(true);
    setNotice(null);
    try {
      const result = await speak({ persona: personaBody(persona), history, sampling: readSampling() });
      history.push({ role: "character", content: result.reply });
      setTurns(history.slice());
    } catch (err) {
      history.pop();
      setTurns(history.slice());
      setInput(text);
      setNotice(err.message === "Not loaded." ? "Pygmalion is not loaded yet. Load it to get a reply." : err.message);
    } finally {
      setBusy(false);
    }
  };

  const live = chosen && model && chosen.repo_id === model.model ? model.detail : chosen?.detail;

  return (
    <div className={styles.layout}>
      <section className={styles.chat}>
        <div className={styles.chatHeader}>
          <h2>{persona?.name || "Basalisk"}</h2>
          <span>{chosen ? `${chosen.name} · ${live || "Checking the model…"}` : "No model on the shelf yet."}</span>
        </div>

        <div className={styles.messages}>
          {missing && <div className={styles.empty}>No figure yet. Start one under Name.</div>}
          {persona?.greeting && turns.length === 0 && (
            <div className={styles.bubbleAgent}>{persona.greeting}</div>
          )}
          {turns.map((turn, index) => (
            <div key={index} className={turn.role === "you" ? styles.bubbleUser : styles.bubbleAgent}>
              {turn.content}
            </div>
          ))}
          {busy && <div className={styles.typing}>{persona?.name || "Pygmalion"} is writing…</div>}
          {notice && <div className={styles.typing}>{notice}</div>}
          <div ref={bottomRef} />
        </div>

        <form className={styles.inputRow} onSubmit={send}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Message Basalisk…"
            aria-label="chat input"
            disabled={busy || !persona}
          />
          <button type="submit" className={`btn btn--sm ${styles.sendBtn}`} disabled={busy || !persona}>
            Send
          </button>
        </form>
      </section>
    </div>
  );
}

const bodyText = (body) => body?.text || body?.topic || JSON.stringify(body);
const replyText = (reply) =>
  typeof reply?.draft === "string" ? reply.draft : JSON.stringify(reply, null, 2);

function KernelThreads() {
  // Selection lives in the URL: /:agentId for an agent folder,
  // /:agentId/:chatId for a chat thread, "/" for a new chat.
  const { agentId, chatId } = useParams();
  const navigate = useNavigate();
  const selected = chatId || agentId || "new";

  const [agents, setAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [notice, setNotice] = useState(null);
  const [offline, setOffline] = useState(false);
  const bottomRef = useRef(null);
  const focusSeqRef = useRef(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const [a, m, f] = await Promise.all([
          fetch("/kernel/agents"),
          fetch("/kernel/messages"),
          fetch("/kernel/focus"),
        ]);
        if (!a.ok || !m.ok) throw new Error();
        const agentList = (await a.json()).agents;
        setAgents(agentList);
        setMessages((await m.json()).messages.slice().reverse()); // oldest first
        if (f.ok) {
          // The kernel can direct UI focus (e.g. a chat forwarded a message
          // to a better-matching chat) — follow it, URL included.
          const focus = await f.json();
          if (focusSeqRef.current === null) {
            focusSeqRef.current = focus.seq;
          } else if (focus.seq > focusSeqRef.current) {
            focusSeqRef.current = focus.seq;
            if (focus.chat) {
              const owner = agentList.find((x) => x.name === focus.chat)?.agent || "editor";
              navigate(`/${owner}/${focus.chat}`);
              setNotice(`Kernel forwarded this conversation to ${focus.chat}.`);
            }
          }
        }
        setOffline(false);
      } catch {
        setOffline(true);
      }
    };
    poll();
    const id = setInterval(poll, 400);
    return () => clearInterval(id);
  }, [navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, selected]);

  const current = agents.find((a) => a.name === selected);
  const chat = messages.filter((m) => m.sender === selected || m.target === selected);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    setNotice(null);
    if (selected === "new") {
      // Unaddressed message: the kernel router decides whether this continues
      // an existing chat thread or spawns a new one.
      const res = await fetch("/kernel/chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, work_seconds: 1.0 }),
      });
      if (!res.ok) return setNotice("kernel rejected the message");
      const data = await res.json();
      navigate(`/${data.agent || "editor"}/${data.chat}`);
      if (data.routed_to_existing) {
        setNotice(`Looks like a continuation — routed to existing thread ${data.chat}.`);
      }
    } else {
      const body =
        current?.kind === "chat" ? { text, work_seconds: 1.0 } : { topic: text, work_seconds: 1.0 };
      await fetch("/kernel/send_async", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: selected, body }),
      });
    }
  };

  const renderMessage = (m) => {
    if (m.sender === "browser") {
      return (
        <div key={m.msg_id} style={{ display: "contents" }}>
          <div className={styles.bubbleUser}>{bodyText(m.body)}</div>
          {m.status === "replied" && (
            <>
              {m.reply?.forwarded_to && (
                <div className={styles.typing}>
                  ↪ forwarded to {m.reply.forwarded_to} (better context match)
                </div>
              )}
              <div className={styles.bubbleAgent}>{replyText(m.reply)}</div>
            </>
          )}
          {m.status === "failed" && (
            <div className={styles.bubbleAgent} style={{ color: "#dc2626" }}>
              failed: {m.error}
            </div>
          )}
          {(m.status === "pending" || m.status === "received") && (
            <div className={styles.typing}>
              {m.target} is working — you are {m.status === "pending" ? "SEND" : "REPLY"}-blocked…
            </div>
          )}
        </div>
      );
    }
    const outgoing = m.sender === selected;
    return (
      <div key={m.msg_id} className={styles.delegation}>
        <div className={styles.delegationTitle}>
          {outgoing ? `MsgSend → ${m.target}` : `MsgReceive ← ${m.sender}`} [{m.status}]
          {m.body?.forwarded ? " (forwarded)" : ""}
        </div>
        {bodyText(m.body)}
        {m.reply && (
          <div style={{ marginTop: "0.3rem", opacity: 0.8 }}>↩ {replyText(m.reply)}</div>
        )}
      </div>
    );
  };

  return (
    <div className={styles.layout}>
      <section className={styles.chat}>
        <div className={styles.chatHeader}>
          <h2>{selected === "new" ? "New chat" : current?.title || selected}</h2>
          {current && (
            <span>
              {current.kind === "chat" && current.agent ? `assigned to ${current.agent} · ` : ""}
              {current.state.replace("_", "-")}
              {current.waiting_on ? ` → blocked on ${current.waiting_on}` : ""}
            </span>
          )}
          {offline && <span style={{ color: "#dc2626" }}>kernel offline — run `uv run darcos-kernel`</span>}
        </div>

        <div className={styles.messages}>
          {selected === "new" ? (
            <div className={styles.empty}>
              Ask anything. If it reads like a continuation of an existing chat, Basalisk routes it
              there; otherwise it spawns a new chat thread under the best-matching agent. Every
              chat is a kernel thread — it blocks, QNX-style, on the threads it calls.
            </div>
          ) : chat.length === 0 ? (
            <div className={styles.empty}>no messages on this thread yet</div>
          ) : (
            chat.map(renderMessage)
          )}
          {notice && <div className={styles.typing}>{notice}</div>}
          <div ref={bottomRef} />
        </div>

        <form className={styles.inputRow} onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              selected === "new"
                ? "Message Basalisk…"
                : `Message ${current?.title || selected}…`
            }
            aria-label="chat input"
          />
          <button type="submit" className={`btn btn--sm ${styles.sendBtn}`}>
            Send
          </button>
        </form>
      </section>
    </div>
  );
}

export default function Threads() {
  const { agentId, chatId } = useParams();
  if (!agentId && !chatId) return <PygmalionChat />;
  return <KernelThreads />;
}
