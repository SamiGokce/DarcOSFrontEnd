import { NavLink, useLocation } from 'react-router-dom';
import { FIGURE_SECTIONS } from '../persona/store';
import styles from './PrimaryBar.module.css';

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function Mark({ children }) {
  return (
    <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true">
      {children}
    </svg>
  );
}

function ThreadsIcon() {
  return (
    <Mark>
      <path {...stroke} d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
    </Mark>
  );
}

function FiguresIcon() {
  return (
    <Mark>
      <circle {...stroke} cx="12" cy="8" r="3.2" />
      <path {...stroke} d="M5.5 19.2a6.5 6.5 0 0 1 13 0" />
    </Mark>
  );
}

function ModelIcon() {
  return (
    <Mark>
      <rect {...stroke} x="7" y="7" width="10" height="10" rx="1.6" />
      <path {...stroke} d="M9 3.8v3.2M12 3.8v3.2M15 3.8v3.2M9 17v3.2M12 17v3.2M15 17v3.2M3.8 9H7M3.8 12H7M3.8 15H7M17 9h3.2M17 12h3.2M17 15h3.2" />
    </Mark>
  );
}

function SettingsIcon() {
  return (
    <Mark>
      <path {...stroke} d="M4 7h16M4 12h16M4 17h16" />
      <circle {...stroke} cx="8" cy="7" r="2" />
      <circle {...stroke} cx="15" cy="12" r="2" />
      <circle {...stroke} cx="10" cy="17" r="2" />
    </Mark>
  );
}

function ReferenceIcon() {
  return (
    <Mark>
      <path {...stroke} d="M12 6.4C10.2 5.1 7.6 4.7 4.5 5.1v12.2c3-.4 5.6 0 7.5 1.3 1.9-1.3 4.5-1.7 7.5-1.3V5.1c-3.1-.4-5.7 0-7.5 1.3Z" />
      <path {...stroke} d="M12 6.4v12.2" />
    </Mark>
  );
}

const SECTIONS = [
  { to: '/', label: 'Threads', end: true, icon: ThreadsIcon },
  { to: '/figures', label: 'Figures', persona: true, icon: FiguresIcon },
  { to: '/model', label: 'Model', icon: ModelIcon },
  { to: '/reference', label: 'Reference', icon: ReferenceIcon },
];

export default function PrimaryBar() {
  const { pathname } = useLocation();
  const [section, soulId] = pathname.split('/').filter(Boolean);
  const carry = FIGURE_SECTIONS.includes(section) ? soulId : null;

  return (
    <nav className={styles.rail} aria-label="Primary">
      <div className={styles.logo} title="Basalisk" aria-label="Basalisk">
        <Mark>
          <path {...stroke} d="M8 4.5v15h4.2c5.2 0 5.2-15 0-15H8Z" />
        </Mark>
      </div>

      <div className={styles.sections}>
        {SECTIONS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.persona && carry ? `${item.to}/${carry}` : item.to}
              end={item.end}
              title={item.label}
              aria-label={item.label}
              className={({ isActive }) => (isActive ? `${styles.item} ${styles.itemActive}` : styles.item)}
            >
              <Icon />
            </NavLink>
          );
        })}
      </div>

      <NavLink
        to="/settings"
        title="Settings"
        aria-label="Settings"
        className={({ isActive }) => (isActive ? `${styles.item} ${styles.itemActive} ${styles.dock}` : `${styles.item} ${styles.dock}`)}
      >
        <SettingsIcon />
      </NavLink>
    </nav>
  );
}
