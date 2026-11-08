import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { createSoul, listSouls } from '../api/forge';
import { SOUL_CHANGED, announceSoulChange } from '../persona/store';
import bar from './SecondaryBar.module.css';

export function FigureRows({ base }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const selected = pathname.slice(base.length).split('/').filter(Boolean)[0];
  const [souls, setSouls] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const read = () => listSouls().then(setSouls).catch((err) => setError(err.message));
    read();
    window.addEventListener(SOUL_CHANGED, read);
    return () => window.removeEventListener(SOUL_CHANGED, read);
  }, [selected]);

  const startNew = async () => {
    const name = window.prompt('Name for the new figure:');
    if (!name?.trim()) return;
    try {
      const soul = await createSoul(name.trim());
      announceSoulChange();
      navigate(`${base}/${soul.slug}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <button type="button" className={bar.link} onClick={startNew}>＋ New figure</button>
      {souls.map((soul) => (
        <NavLink
          key={soul.slug}
          to={`${base}/${soul.slug}`}
          className={soul.slug === selected ? `${bar.link} ${bar.linkActive}` : bar.link}
        >
          <span className={bar.linkName}>{soul.name}</span>
          <span className={bar.linkMeta}>{soul.file}</span>
        </NavLink>
      ))}
      {souls.length === 0 && !error && <div className={bar.linkMeta}>No figures yet.</div>}
      {error && <div className={bar.offline}>{error}</div>}
    </>
  );
}

export default function PersonaList() {
  return (
    <aside className={bar.bar} aria-label="Figures">
      <div className={bar.title}>Figures</div>
      <FigureRows base="/figures" />
    </aside>
  );
}
