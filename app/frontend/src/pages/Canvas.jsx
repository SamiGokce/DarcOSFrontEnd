import { useState } from "react";
import { useDrag, useDrop } from "react-dnd";

const InstructionItem = ({ instruction, index }) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: "instruction",
    item: { index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }));

  return (
    <li
      ref={drag}
      className={`sidebar-list__row sidebar-list__row--draggable${isDragging ? " is-dragging" : ""}`}
    >
      <span className="sidebar-list__grip" aria-hidden="true" />
      <span className="sidebar-list__label sidebar-list__label--mono">{instruction}</span>
    </li>
  );
};

const ControlItem = ({ label, onClick }) => (
  <li
    className="sidebar-list__row sidebar-list__row--action"
    onClick={onClick}
    onKeyDown={(e) => {
      if (onClick && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        onClick();
      }
    }}
    tabIndex={onClick ? 0 : undefined}
    role={onClick ? "menuitem" : undefined}
  >
    <span className="sidebar-list__label">{label}</span>
  </li>
);

export default function Canvas() {
  const [instructions] = useState(["ADD", "ADDI", "NOP", "HALT"]);
  const [program, setProgram] = useState([]);

  const [, drop] = useDrop(() => ({
    accept: "instruction",
    drop: (item) => {
      setProgram((prev) => [...prev, instructions[item.index]]);
    },
  }));

  const load = () => {
    console.log("Loaded program:", program);
  };

  const controls = [
    { id: "compile", label: "Compile & Load", onClick: load },
    { id: "step", label: "Step" },
    { id: "reset", label: "Reset" },
    { id: "save", label: "Save Program" },
    { id: "load-program", label: "Load Program" },
    { id: "clear", label: "Clear Saved" },
    { id: "export", label: "Export JSON" },
  ];

  return (
    <div className="page page--canvas fade-in">
      <div className="canvas-layout">
        <aside className="sidebar sidebar--left sidebar--fit glass glass-panel">
          <h2 className="sidebar__title">Instructions</h2>
          <ul className="sidebar-list">
            {instructions.map((instruction, index) => (
              <InstructionItem
                key={`${instruction}-${index}`}
                index={index}
                instruction={instruction}
              />
            ))}
          </ul>
        </aside>

        <main
          ref={drop}
          className="canvas-main glass glass-panel glass-panel--wide"
        >
          <h2 className="sidebar__title">Program</h2>
          <div className="drop-zone drop-zone--canvas">
            {program.length === 0 ? (
              <p className="drop-zone__placeholder">Drag instructions here</p>
            ) : (
              <p className="program-list">{program.join(", ")}</p>
            )}
          </div>
        </main>

        <aside className="sidebar sidebar--right sidebar--fit glass glass-panel">
          <h2 className="sidebar__title">Controls</h2>
          <ul className="sidebar-list">
            {controls.map(({ id, label, onClick }) => (
              <ControlItem key={id} label={label} onClick={onClick} />
            ))}
            <li className="sidebar-list__row sidebar-list__row--action">
              <label htmlFor="file-upload" className="sidebar-list__label">
                Choose File
              </label>
              <input id="file-upload" type="file" />
            </li>
          </ul>
        </aside>
      </div>
    </div>
  );
}
