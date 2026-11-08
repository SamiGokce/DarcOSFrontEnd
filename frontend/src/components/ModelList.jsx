import { useEffect, useState } from 'react';
import { NavLink, useLocation, useSearchParams } from 'react-router-dom';
import { listModels } from '../api/forge';
import bar from './SecondaryBar.module.css';

export default function ModelList({ manage }) {
  const { pathname } = useLocation();
  const [params] = useSearchParams();
  const selected = manage ? pathname.split('/').filter(Boolean)[1] : params.get('model');
  const [models, setModels] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let stopped = false;
    const read = () =>
      listModels()
        .then((rows) => {
          if (!stopped) setModels(rows);
        })
        .catch((err) => {
          if (!stopped) setError(err.message);
        });
    read();
    const id = setInterval(read, 800);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, []);

  return (
    <aside className={bar.bar} aria-label="Models">
      <div className={bar.title}>Models</div>
      <NavLink to="/model" end className={({ isActive }) => (isActive ? `${bar.link} ${bar.linkActive}` : bar.link)}>
        <span className={bar.linkName}>＋ New model</span>
      </NavLink>
      {models.map((model) => {
        const to = manage ? `/model/${model.id}` : `/?model=${model.id}`;
        const active = String(model.id) === String(selected);
        return (
          <NavLink key={model.id} to={to} className={active ? `${bar.link} ${bar.linkActive}` : bar.link}>
            <span className={bar.linkName}>{model.name}</span>
            <span className={bar.linkMeta}>{model.state === 'ready' ? 'loaded' : model.download_state === 'downloading' ? `${model.download_percent || 0}%` : model.state}</span>
            {model.download_state === 'downloading' && (
              <span className={bar.meter} aria-hidden="true">
                <span className={bar.meterFill} style={{ width: `${model.download_percent || 0}%` }} />
              </span>
            )}
          </NavLink>
        );
      })}
      {error && <div className={bar.offline}>{error}</div>}
    </aside>
  );
}
