import { useState } from "react";
import { useDrag, useDrop } from "react-dnd";
import "../assets/base.css"; // For global styles (glass effect)

const InstructionButton = ({ instruction, index }) => {
  const [, drag] = useDrag(() => ({
    type: "instruction", // Drag type
    item: { index },     // The dragged item (instruction index)
  }));

  return (
    <button
      ref={drag} // Attach drag functionality to the button
      className="instruction-button"
      style={{
        backgroundColor: "rgba(220, 240, 255, 0.5)",  // Light background for the buttons
        padding: "12px",
        marginBottom: "15px",
        borderRadius: "8px",
        cursor: "move",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
      }}
    >
      {instruction}
    </button>
  );
};

export default function Canvas() {
  const [instructions, setInstructions] = useState(["ADD", "ADDI", "NOP", "HALT"]);
  const [program, setProgram] = useState([]); // Holds the instructions dropped into the program board

  const moveInstruction = (fromIndex, toIndex) => {
    const updatedInstructions = [...instructions];
    const [movedItem] = updatedInstructions.splice(fromIndex, 1);
    updatedInstructions.splice(toIndex, 0, movedItem);
    setInstructions(updatedInstructions);  // Update the instructions state
  };

  const [, drop] = useDrop(() => ({
    accept: "instruction",  // Accept instructions being dragged
    drop: (item) => {
      // Add the dropped instruction to the program
      setProgram((prev) => [...prev, instructions[item.index]]);
    },
  }));

  const load = () => {
    // Assuming your instructions are being added as machine code
    console.log("Loaded program:", program);
    // Call the loadProgram function with the program state here
  };

  return (
    <div style={{ padding: "2.5rem 2rem" }} className="fade-in">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "200px 1fr 250px",
          gap: "2.5rem",
          alignItems: "start",
        }}
      >
        {/* Left side: Instruction Buttons */}
        <div>
          <h2
            style={{
              fontWeight: 600,
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
              marginBottom: "1rem",
            }}
          >
            Instructions
          </h2>
          <div className="instruction-group">
            {instructions.map((instruction, index) => (
              <InstructionButton key={instruction} index={index} instruction={instruction} />
            ))}
          </div>
        </div>

        {/* Middle: Program Board (Drop Zone) */}
        <div
          ref={drop} // Attach the drop functionality to this div
          className="glass"
          style={{
            padding: "1.8rem",
            borderRadius: "18px",
            minHeight: "300px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.04)",
          }}
        >
          <h2
            style={{
              fontWeight: 600,
              marginBottom: "1.2rem",
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
            }}
          >
            Program
          </h2>
          <div
            style={{
              background: "linear-gradient(145deg, rgba(34, 72, 174, 0.4), rgba(64, 89, 204, 0.4))",
              borderRadius: "12px",
              padding: "1rem",
              textAlign: "center",
              color: "#1a1a1a",
              fontWeight: 500,
              boxShadow: "inset 0 1px 4px rgba(118, 148, 199, 0.3)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
            }}
          >
            {program.length === 0 ? (
              "Drag Instructions Here"
            ) : (
              <div>{program.join(", ")}</div>  // Display the program's instructions
            )}
          </div>
        </div>

        {/* Right: Control Panel */}
        <div>
          <div className="sim-button-group">
            <button className="sim-button" onClick={load}>
              Compile & Load
            </button>
            <button className="sim-button">Step</button>
            <button className="sim-button">Reset</button>
            <button className="sim-button">Save Program</button>
            <button className="sim-button">Load Program</button>
            <button className="sim-button">Clear Saved</button>
            <button className="sim-button">Export JSON</button>
          </div>

          <label
            htmlFor="file-upload"
            className="file-upload"
            style={{
              marginTop: "1.2rem",
              display: "block",
              textAlign: "center",
              fontWeight: 500,
            }}
          >
            Choose File
          </label>
          <input
            id="file-upload"
            type="file"
            style={{
              marginTop: "0.5rem",
              padding: "0.8rem 1.2rem",
              borderRadius: "8px",
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
              border: "1px solid rgba(0, 0, 0, 0.15)",
              backgroundColor: "rgba(240, 240, 255, 0.3)",
              boxShadow: "0 4px 8px rgba(0, 0, 0, 0.2)",
              fontWeight: 500,
            }}
          />
        </div>
      </div>
    </div>
  );
}
