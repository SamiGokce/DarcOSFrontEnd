import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import SimStep from "./pages/SimStep";
import MemoryConsole from "./pages/MemoryConsole";
import Registers from "./pages/Registers";
import History from "./pages/History";
import Canvas from "./pages/Canvas";
import IsaReference from "./pages/IsaReference";
import { DndProvider } from "react-dnd";  // Import DndProvider
import { HTML5Backend } from "react-dnd-html5-backend"; // Import HTML5Backend for drag-and-drop

import './assets/base.css'; // Ensure this is imported in your root file

export default function App() {
  return (
    <DndProvider backend={HTML5Backend}>  {/* Wrap the app with DndProvider */}
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/step" element={<SimStep />} />
        <Route path="/memory" element={<MemoryConsole />} />
        <Route path="/registers" element={<Registers />} />
        <Route path="/history" element={<History />} />
        <Route path="/canvas" element={<Canvas />} />
        <Route path="/isa" element={<IsaReference />} />
      </Routes>
    </DndProvider>
  );
}
