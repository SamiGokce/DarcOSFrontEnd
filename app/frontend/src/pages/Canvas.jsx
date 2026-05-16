import { useState } from "react";
import { useDrag, useDrop } from "react-dnd";

const InstructionButton = ({ instruction, index }) => {
  const [, drag] = useDrag(() => ({
    type: "instruction",
    item: { index },
  }));

  return (
    <button
      ref={drag}
      type="button"
      className="instruction-button instruction-button--drag"
    >
      {instruction}
    </button>
  );
};

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

  return (
    <div className="page page--compact">
      <div className="page-grid page-grid--3">
        <section>
          <h2 className="glass-panel__title">Instructions</h2>
          <div className="instruction-group">
            {instructions.map((instruction, index) => (
              <InstructionButton
                key={`${instruction}-${index}`}
                index={index}
                instruction={instruction}
              />
            ))}
          </div>
        </section>

        <section ref={drop} className="glass glass-panel glass-panel--wide">
          <h2 className="glass-panel__title glass-panel__title--spaced">Program</h2>
          <div className="drop-zone">
            {program.length === 0 ? (
              "Drag Instructions Here"
            ) : (
              <div>{program.join(", ")}</div>
            )}
          </div>
        </section>

        <aside>
          <div className="sim-button-group">
            <button type="button" className="sim-button" onClick={load}>
              Compile & Load
            </button>
            <button type="button" className="sim-button">
              Step
            </button>
            <button type="button" className="sim-button">
              Reset
            </button>
            <button type="button" className="sim-button">
              Save Program
            </button>
            <button type="button" className="sim-button">
              Load Program
            </button>
            <button type="button" className="sim-button">
              Clear Saved
            </button>
            <button type="button" className="sim-button">
              Export JSON
            </button>
          </div>

          <label htmlFor="file-upload" className="file-upload file-upload--spaced">
            Choose File
          </label>
          <input id="file-upload" type="file" />
        </aside>
      </div>
    </div>
  );
}
