import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { createPersona, listPersonas } from '../api/forge';
import { blankPersona } from '../persona/store';
import bar from './SecondaryBar.module.css';

export function FigureRows({ base }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const selected = pathname.slice(base.length).split('/').filter(Boolean)[0];
  const [personas, setPersonas] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    listPersonas().then(setPersonas).catch((err) => setError(err.message));
  }, [selected]);

  const startNew = async () => {
    try {
      const saved = await createPersona({ ...blankPersona(), name: 'Untitled' });
      navigate(`${base}/${saved.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <button type="button" className={bar.link} onClick={startNew}>＋ New figure</button>
      {personas.map((persona) => (
        <NavLink
          key={persona.id}
          to={`${base}/${persona.id}`}
          className={String(persona.id) === String(selected) ? `${bar.link} ${bar.linkActive}` : bar.link}
        >
          <span className={bar.linkName}>{persona.name}</span>
          <span className={bar.linkMeta}>{persona.epithet || 'No epithet'}</span>
        </NavLink>
      ))}
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
