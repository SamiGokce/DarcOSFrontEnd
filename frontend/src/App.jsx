import { Navigate, Route, Routes, useParams } from "react-router-dom";
import PrimaryBar from "./components/PrimaryBar";
import SecondaryBar from "./components/SecondaryBar";
import Threads from "./pages/Threads";
import Figure from "./pages/Figure";
import Model from "./pages/Model";
import Settings from "./pages/Settings";
import System from "./pages/System";
import Reference from "./pages/Reference";
import styles from "./App.module.css";

function ToFigure() {
  const { personaId } = useParams();
  return <Navigate to={personaId ? `/figures/${personaId}` : "/figures"} replace />;
}

function ToSystem() {
  const { part } = useParams();
  return <Navigate to={`/settings/system/${part || "channels"}`} replace />;
}

const LEGACY_FIGURES = ["name", "soul", "form", "world", "voice", "speak", "mold"];

export default function App() {
  return (
    <div className={styles.frame}>
      <PrimaryBar />
      <SecondaryBar />
      <div className={styles.stage}>
        <Routes>
          <Route path="/" element={<Threads />} />
          <Route path="/figures/:personaId?" element={<Figure base="/figures" />} />
          <Route path="/settings/system/agents/:personaId?" element={<Figure base="/settings/system/agents" />} />
          {LEGACY_FIGURES.map((name) => (
            <Route key={name} path={`/${name}/:personaId?`} element={<ToFigure />} />
          ))}
          <Route path="/agents" element={<Navigate to="/figures" replace />} />
          <Route path="/model/load" element={<Navigate to="/model" replace />} />
          <Route path="/model/sampling" element={<Navigate to="/model" replace />} />
          <Route path="/model" element={<Model />} />
          <Route path="/model/:modelId" element={<Model />} />
          <Route path="/settings" element={<Navigate to="/settings/account" replace />} />
          <Route path="/settings/:part" element={<Settings />} />
          <Route path="/settings/system" element={<Navigate to="/settings/system/channels" replace />} />
          <Route path="/settings/system/:part" element={<System />} />
          <Route path="/system" element={<ToSystem />} />
          <Route path="/system/:part" element={<ToSystem />} />
          <Route path="/reference" element={<Navigate to="/reference/syscalls" replace />} />
          <Route path="/reference/:part" element={<Reference />} />
          <Route path="/:agentId" element={<Threads />} />
          <Route path="/:agentId/:chatId" element={<Threads />} />
        </Routes>
      </div>
    </div>
  );
}
