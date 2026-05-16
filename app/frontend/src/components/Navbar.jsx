import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthModal from './AuthModal';
import styles from './Navbar.module.css';

const navLinkClass =
  ({ isActive }) => (isActive ? `${styles.link} ${styles.linkActive}` : styles.link);

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [authModal, setAuthModal] = useState(null);

  return (
    <>
      <nav className={styles.navbar}>
        <div className={styles.logo}>DarcOS</div>

        <div className={styles.links}>
          <NavLink to="/" className={navLinkClass} end>
            Home
          </NavLink>
          <NavLink to="/canvas" className={navLinkClass}>
            Canvas
          </NavLink>
          <NavLink to="/step" className={navLinkClass}>
            Step
          </NavLink>
          <NavLink to="/registers" className={navLinkClass}>
            Registers
          </NavLink>
          <NavLink to="/history" className={navLinkClass}>
            History
          </NavLink>
          <NavLink to="/memory" className={navLinkClass}>
            Memory
          </NavLink>
          <NavLink to="/isa" className={navLinkClass}>
            ISA Reference
          </NavLink>
        </div>

        <div className={styles.controls}>
          {isAuthenticated ? (
            <>
              <span className={styles.userLabel}>{user.username}</span>
              <button type="button" className="btn btn--sm btn--ghost" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                onClick={() => setAuthModal('login')}
              >
                Log in
              </button>
              <button
                type="button"
                className="btn btn--sm"
                onClick={() => setAuthModal('signup')}
              >
                Sign up
              </button>
            </>
          )}
        </div>
      </nav>

      {authModal && (
        <AuthModal
          mode={authModal}
          onClose={() => setAuthModal(null)}
          onSwitchMode={setAuthModal}
        />
      )}
    </>
  );
}
