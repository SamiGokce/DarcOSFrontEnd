import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav style={{ background: "black", padding: "1rem", display: "flex", justifyContent: "space-between" }}>
      <h1 style={{ color: "white" }}>DarcOS</h1>
      <div>
        <Link to="/" style={{ color: "white", margin: "0 1rem" }}>Home</Link>
        <Link to="/projects" style={{ color: "white", margin: "0 1rem" }}>Projects</Link>
        <Link to="/about" style={{ color: "white", margin: "0 1rem" }}>About</Link>
      </div>
    </nav>
  );
}

export default Navbar;
