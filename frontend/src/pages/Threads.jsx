import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { createChat, deleteChat, getChat, listModels, listSouls, modelStatus, sendMessage } from "../api/forge";
import { CHAT_CHANGED, SOUL_CHANGED, announceChatChange } from "../persona/store";
import styles from "./Threads.module.css";

const SAMPLING_KEY = "basalisk.modelSampling";

function readSampling() {
  try {
    return JSON.parse(localStorage.getItem(SAMPLING_KEY) || "{}");
  } catch {
    return {};
  }
}

function pickModel(models, status) {
  return (
    models.find((model) => model.repo_id === status?.model && status?.state === "ready") ||
    models.find((model) => model.download_state === "downloaded") ||
    models[0] ||
    null
  );
}

function PygmalionChat() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const chatId = params.get("chat");
  const soulParam = params.get("soul");

  const [souls, setSouls] = useState([]);
  const [models, setModels] = useState([]);
  const [status, setStatus] = useState(null);
  const [chat, setChat] = useState(null);
  const [soulSlug, setSoulSlug] = useState("");
  const [modelId, setModelId] = useState("");
  const [input, setInput] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("write");
  const [notice, setNotice] = useState(null);
  const [trace, setTrace] = useState(null);
  const bottomRef = useRef(null);
  const createdRef = useRef(null);

  useEffect(() => {
    const read = () => listSouls().then(setSouls).catch((err) => setNotice(err.message));
    read();
    window.addEventListener(SOUL_CHANGED, read);
    return () => window.removeEventListener(SOUL_CHANGED, read);
  }, []);

  useEffect(() => {
    let stopped = false;
    const read = () => {
      modelStatus()
        .then((next) => {
          if (!stopped) setStatus(next);
        })
        .catch(() => {});
      listModels()
        .then((rows) => {
          if (!stopped) setModels(rows);
        })
        .catch(() => {});
    };
    read();
    const id = setInterval(read, busy ? 800 : 2500);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [busy]);

  useEffect(() => {
    let stopped = false;
    if (chatId && createdRef.current === chatId) {
      createdRef.current = null;
      return undefined;
    }
    setTrace(null);
    setNotice(null);
    if (!chatId) {
      setChat(null);
      return undefined;
    }
    getChat(chatId)
      .then((loaded) => {
        if (stopped) return;
        setChat(loaded);
        setSoulSlug(loaded.soul);
      })
      .catch((err) => {
        if (!stopped) {
          setChat(null);
          setNotice(err.message);
        }
      });
    return () => {
      stopped = true;
    };
  }, [chatId]);

  useEffect(() => {
    if (chat) {
      const match = models.find((model) => model.repo_id === chat.repo_id);
      if (match) setModelId(String(match.id));
      return;
    }
    if (soulParam) setSoulSlug(soulParam);
    else if (!soulSlug && souls[0]) setSoulSlug(souls[0].slug);
    if (!modelId && models.length) {
      const pick = pickModel(models, status);
      if (pick) setModelId(String(pick.id));
    }
  }, [chat, models, souls, soulParam, status, soulSlug, modelId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.messages?.length, pending, busy]);

  const soul = souls.find((item) => item.slug === soulSlug) || null;
  const model = models.find((item) => String(item.id) === String(modelId)) || null;
  const repoId = chat?.repo_id || model?.repo_id;
  const modelName = chat?.model_name || model?.name;
  const ready = status?.state === "ready" && status?.model === repoId;
  const live = ready ? status.detail : model?.state === "downloading" ? model.detail : model?.download_state === "downloaded" ? "Downloaded · loads on the first message" : model?.detail;

  const startFresh = (nextSoul, nextModel) => {
    if (nextSoul !== undefined) setSoulSlug(nextSoul);
    if (nextModel !== undefined) setModelId(nextModel);
    navigate(`/?soul=${encodeURIComponent(nextSoul ?? soulSlug)}`);
  };

  const send = async (event) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy || !soul || !model) return;
    setInput("");
    setPending(text);
    setBusy(true);
    setNotice(null);
    setPhase(ready ? "write" : "load");
    let created = null;
    try {
      const target = chat || (created = await createChat(soul.slug, model.id));
      const result = await sendMessage(target.id, text, readSampling());
      setTrace({ prompt: result.prompt, memories: result.memories, sections: result.soul_sections });
      announceChatChange();
      if (created) {
        setChat({ ...created, messages: [result.message, result.reply] });
        createdRef.current = String(created.id);
        navigate(`/?chat=${created.id}`);
      } else {
        setChat((current) => ({ ...current, messages: [...current.messages, result.message, result.reply] }));
      }
    } catch (err) {
      if (created) await deleteChat(created.id).catch(() => {});
      setInput(text);
      setNotice(err.message);
    } finally {
      setPending("");
      setBusy(false);
    }
  };

  const messages = chat?.messages || [];
  const name = soul?.name || chat?.soul || "Basalisk";

  return (
    <div className={styles.layout}>
      <section className={styles.chat}>
        <div className={styles.chatHeader}>
          <h2>{name}</h2>
          <select
            className={styles.picker}
            aria-label="Figure"
            value={soulSlug}
            onChange={(event) => startFresh(event.target.value, undefined)}
            disabled={busy || souls.length === 0}
          >
            {souls.length === 0 && <option value="">No figures</option>}
            {souls.map((item) => (
              <option key={item.slug} value={item.slug}>{item.name}</option>
            ))}
          </select>
          <select
            className={styles.picker}
            aria-label="Model"
            value={modelId}
            onChange={(event) => startFresh(undefined, event.target.value)}
            disabled={busy || models.length === 0}
          >
            {models.length === 0 && <option value="">No models</option>}
            {models.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}{item.download_state === "downloaded" ? "" : " (not downloaded)"}
              </option>
            ))}
          </select>
          <span>{modelName ? `${modelName} · ${live || "Checking the model…"}` : ""}</span>
          <button type="button" className="btn btn--sm btn--ghost" onClick={() => startFresh()} disabled={busy || !chat}>
            New chat
          </button>
        </div>

        <div className={styles.messages}>
          {souls.length === 0 && (
            <div className={styles.empty}>
              No figures yet. Draft a soul.md under Figures, then test it here.
              <div>
                <button type="button" className="btn btn--sm" onClick={() => navigate("/figures")}>Open Figures</button>
              </div>
            </div>
          )}
          {souls.length > 0 && !chat && !pending && (
            <div className={styles.empty}>
              New chat with {name}{modelName ? ` on ${modelName}` : ""}. Each model gets its own chat, so switching models starts fresh.
              Earlier turns are recalled by relevance once the chat grows.
            </div>
          )}
          {messages.map((message) => (
            <div key={message.id} className={message.role === "you" ? styles.bubbleUser : styles.bubbleAgent}>
              {message.content}
            </div>
          ))}
          {pending && <div className={styles.bubbleUser}>{pending}</div>}
          {busy && (
            <div className={styles.typing}>
              {phase === "load" ? `Loading ${modelName || "the model"}…` : `${name} is writing…`}
            </div>
          )}
          {trace && !busy && (
            <details className={styles.trace}>
              <summary>
                {trace.memories.length
                  ? `Recalled ${trace.memories.length} earlier exchange${trace.memories.length === 1 ? "" : "s"}`
                  : "No earlier exchanges recalled"}
                {" · prompt"}
              </summary>
              {trace.memories.length > 0 && (
                <ul>
                  {trace.memories.map((memory, index) => (
                    <li key={index}>{memory}</li>
                  ))}
                </ul>
              )}
              <pre>{trace.prompt}</pre>
            </details>
          )}
          {notice && <div className={styles.typing}>{notice}</div>}
          <div ref={bottomRef} />
        </div>

        <form className={styles.inputRow} onSubmit={send}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={soul ? `Message ${soul.name}…` : "Message Basalisk…"}
            aria-label="chat input"
            disabled={busy || !soul || !model}
          />
          <button type="submit" className={`btn btn--sm ${styles.sendBtn}`} disabled={busy || !soul || !model}>
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
