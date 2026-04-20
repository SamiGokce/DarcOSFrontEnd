import { Link } from "react-router-dom";
import styles from "./Navbar.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.logo}>DarcOS</div>

      <div className={styles.links}>
        <Link to="/">Home</Link>
        <Link to="/canvas">Canvas</Link>
        <Link to="/step">Step</Link>
        <Link to="/registers">Registers</Link>
        <Link to="/signup">Sign Up</Link>
        <Link to="/memory">Memory</Link>
        <Link to="/login">Login</Link>
      </div>

      <div className={styles.controls}>
        <Link to="/login" className={styles.loginButton}>Login</Link>
      </div>
    </nav>
  );
}

