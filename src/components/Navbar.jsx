import { Link } from "react-router-dom";
import styles from "./Navbar.module.css"; // ✅ Import the CSS module

function Navbar() {
  return (
    <nav className={styles.navbar}>
      <h1 className={styles.logo}>DarcOS</h1>
      <div className={styles.links}>
        <Link to="/" className={styles.link}>Home</Link>
        <Link to="/projects" className={styles.link}>Projects</Link>
        <Link to="/about" className={styles.link}>About</Link>
      </div>
    </nav>
  );
}

export default Navbar;
