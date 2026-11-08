import { useEffect, useState } from "react";
import { NavLink, useLocation, useMatch, useNavigate } from "react-router-dom";
import styles from "../pages/Threads.module.css";
import { FIGURE_SECTIONS } from "../persona/store";
import ChatList from "./ChatList";
import ModelList from "./ModelList";
import PersonaList, { FigureRows } from "./PersonaList";
import bar from "./SecondaryBar.module.css";

const RESERVED = new Set([
  ...FIGURE_SECTIONS,
  "agents",
  "model",
  "settings",
  "system",
  "reference",
]);

const STATE_COLORS = {
  running: "#4ade80",
  receive_blocked: "#94a3b8",
  send_blocked: "#f97316",
  reply_blocked: "#facc15",
  dead: "#ef4444",
  ready: "#60a5fa",
};

function StateDot({ state }) {
  return <span className={styles.stateDot} style={{ background: STATE_COLORS[state] || "#999" }} />;
}

function TreeRow({ agent, icon, label, selected, onSelect, expanded, onToggle, onAdd }) {
  const busy = agent && agent.state !== "receive_blocked";
  const tooltip = agent
    ? `${agent.state.replace("_", "-")}${agent.waiting_on ? ` → blocked on ${agent.waiting_on}` : ""}`
    : undefined;
  return (
    <button
      type="button"
      className={`${styles.treeRow} ${selected ? styles.treeRowActive : ""}`}
      onClick={onSelect}
      title={tooltip}
    >
      <span
        className={styles.chevron}
        onClick={
          onToggle
            ? (event) => {
                event.stopPropagation();
                onToggle();
              }
            : undefined
        }
      >
        {onToggle ? (expanded ? "▾" : "▸") : ""}
      </span>
      <span className={styles.treeIcon}>{icon}</span>
      <span className={styles.treeLabel}>{label}</span>
      {busy && (
        <span className={styles.treeState}>
          {agent.state.replace("_", "-")}
          {agent.waiting_on ? ` → ${agent.waiting_on}` : ""}
        </span>
      )}
      {agent && <StateDot state={agent.state} />}
      {onAdd && (
        <span
          className={styles.plus}
          title="New chat under this agent"
          onClick={(event) => {
            event.stopPropagation();
            onAdd();
          }}
        >
          ＋
        </span>
      )}
    </button>
  );
}

function ChatSidebar() {
  const navigate = useNavigate();
  const chatMatch = useMatch("/:agentId/:chatId");
  const folderMatch = useMatch("/:agentId");
  const folderId = folderMatch?.params.agentId;
  const agentId = chatMatch?.params.agentId || (folderId && !RESERVED.has(folderId) ? folderId : null);
  const selected = chatMatch?.params.chatId || agentId || "new";

  const [agents, setAgents] = useState([]);
  const [collapsed, setCollapsed] = useState({});
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let stopped = false;
    const poll = async () => {
      try {
        const response = await fetch("/kernel/agents");
        if (!response.ok) throw new Error();
        if (!stopped) {
          setAgents((await response.json()).agents);
          setOffline(false);
        }
      } catch {
        if (!stopped) setOffline(true);
      }
    };
    poll();
    const id = setInterval(poll, 400);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, []);

  const chats = agents.filter((agent) => agent.kind === "chat");
  const services = agents.filter((agent) => agent.kind !== "chat");

  const newChatUnder = async (agentName) => {
    const response = await fetch("/kernel/chats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent: agentName }),
    });
    if (!response.ok) return;
    const data = await response.json();
    navigate(`/${data.agent}/${data.chat}`);
  };

  const newAgent = async () => {
    const name = window.prompt("Name for the new agent:");
    if (!name?.trim()) return;
    const response = await fetch("/kernel/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) return;
    const data = await response.json();
    navigate(`/${data.agent}`);
  };

  return (
    <aside className={bar.bar} aria-label="Secondary">
      <div className={styles.sidebarTitle}>Agents &amp; their chats</div>
      {offline && <div className={bar.offline}>kernel offline</div>}
      <div className={styles.tree}>
        {services.map((service) => {
          const owned = chats.filter((chat) => chat.agent === service.name);
          const isCollapsed = collapsed[service.name] ?? false;
          return (
            <div key={service.name}>
              <TreeRow
                agent={service}
                icon={isCollapsed ? "📁" : "📂"}
                label={service.name}
                selected={selected === service.name}
                onSelect={() => navigate(`/${service.name}`)}
                expanded={!isCollapsed}
                onToggle={() => setCollapsed((current) => ({ ...current, [service.name]: !isCollapsed }))}
                onAdd={() => newChatUnder(service.name)}
              />
              {!isCollapsed && owned.length > 0 && (
                <div className={styles.folderChildren}>
                  {owned.map((chat) => (
                    <TreeRow
                      key={chat.name}
                      agent={chat}
                      icon="🗒"
                      label={chat.title || chat.name}
                      selected={selected === chat.name}
                      onSelect={() => navigate(`/${service.name}/${chat.name}`)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
        <button type="button" className={styles.newAgentRow} onClick={newAgent}>
          <span className={styles.chevron} />
          <span className={styles.treeIcon}>＋</span>
          <span className={styles.treeLabel}>New agent</span>
        </button>
      </div>
    </aside>
  );
}

const FIGURES_UNDER = "/settings/system/agents";

const MENUS = {
  settings: {
    title: "Settings",
    links: [
      ["/settings/account", "Account"],
      ["/settings/runtime", "Runtime"],
      {
        label: "System",
        children: [
          ["/settings/system/channels", "Channels"],
          ["/settings/system/log", "Log"],
          [FIGURES_UNDER, "Agents"],
        ],
      },
    ],
  },
  reference: {
    title: "Reference",
    links: [
      ["/reference/syscalls", "Syscalls"],
      ["/reference/states", "Thread states"],
      ["/reference/cards", "Agent cards"],
    ],
  },
};

function MenuLink({ to, label }) {
  return (
    <NavLink key={to} to={to} className={({ isActive }) => (isActive ? `${bar.link} ${bar.linkActive}` : bar.link)}>
      <span className={bar.linkName}>{label}</span>
    </NavLink>
  );
}

function Menu({ title, links }) {
  const { pathname } = useLocation();
  return (
    <aside className={bar.bar} aria-label={title}>
      <div className={bar.title}>{title}</div>
      {links.map((entry) =>
        Array.isArray(entry) ? (
          <MenuLink key={entry[0]} to={entry[0]} label={entry[1]} />
        ) : (
          <div key={entry.label}>
            <div className={bar.link}>
              <span className={bar.linkName}>{entry.label}</span>
            </div>
            <div className={bar.nest}>
              {entry.children.map(([to, label]) => (
                <div key={to}>
                  <MenuLink to={to} label={label} />
                  {to === FIGURES_UNDER && pathname.startsWith(FIGURES_UNDER) && (
                    <div className={bar.nest}>
                      <FigureRows base={FIGURES_UNDER} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      )}
    </aside>
  );
}

export default function SecondaryBar() {
  const { pathname } = useLocation();
  const section = pathname.split("/").filter(Boolean)[0] || "";
  if (!section) return <ChatList />;
  if (section === "model") return <ModelList manage />;
  if (FIGURE_SECTIONS.includes(section)) return <PersonaList />;
  if (MENUS[section]) return <Menu {...MENUS[section]} />;
  return <ChatSidebar />;
}
