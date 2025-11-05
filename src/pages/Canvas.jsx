import "../assets/base.css";

export default function Canvas() {
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
        {/* ===== Left: Instruction Buttons ===== */}
        <div>
          <h2
            style={{
              fontWeight: 600,
              fontFamily:
                "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
              marginBottom: "1rem",
            }}
          >
            Instructions
          </h2>
          <div className="instruction-group">
            <button className="instruction-button">ADD</button>
            <button className="instruction-button">ADDI</button>
            <button className="instruction-button">NOP</button>
            <button className="instruction-button">HALT</button>
          </div>
        </div>

        {/* ===== Middle: Program Board ===== */}
        <div
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
              fontFamily:
                "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
            }}
          >
            Program
          </h2>
          <div
            style={{
              background:
                "linear-gradient(145deg, rgba(34, 72, 174, 0.4), rgba(64, 89, 204, 0.4))",
              borderRadius: "12px",
              padding: "1rem",
              textAlign: "center",
              color: "#1a1a1a",
              fontWeight: 500,
              boxShadow: "inset 0 1px 4px rgba(118, 148, 199, 0.3)",
              backdropFilter: "blur(10px)",
              WebkitBackdropFilter: "blur(10px)",
              fontFamily:
                "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
            }}
          >
            ADD
          </div>
        </div>

        {/* ===== Right: Control Panel ===== */}
        <div>
          <div className="sim-button-group">
            <button className="sim-button">Compile & Load</button>
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
              fontFamily:
                "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', sans-serif",
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
