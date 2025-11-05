import { Link } from "react-router-dom";
import { useCpu } from "../context/CpuContext";
import styles from "./Navbar.module.css";

export default function Navbar() {
  const { step, reset } = useCpu();

  return (
    <nav className={styles.navbar}>
      <div className={styles.logo}>DarcOS</div>

      <div className={styles.links}>
        <Link to="/">Home</Link>
        <Link to="/canvas">Canvas</Link>
        <Link to="/step">Step</Link>
        <Link to="/registers">Registers</Link>
        <Link to="/history">History</Link>
        <Link to="/memory">Memory</Link>
        <Link to="/isa">ISA Reference</Link>
      </div>

      <div className={styles.controls}>
        <button onClick={step}>Step</button>
        <button onClick={reset}>Reset</button>
      </div>
    </nav>
  );
}

