import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import SimStep from "./pages/SimStep";
import Registers from "./pages/Registers";
import History from "./pages/History";
import Canvas from "./pages/Canvas";
import IsaReference from "./pages/IsaReference";

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/step" element={<SimStep />} />
        <Route path="/registers" element={<Registers />} />
        <Route path="/history" element={<History />} />
        <Route path="/canvas" element={<Canvas />} />
        <Route path="/isa" element={<IsaReference />} />
      </Routes>
    </>
  );
}
