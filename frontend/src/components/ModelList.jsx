import { useEffect, useState } from 'react';
import { NavLink, useLocation, useSearchParams } from 'react-router-dom';
import { listModels } from '../api/forge';
import bar from './SecondaryBar.module.css';

// The family is the start of the repo, the owner before the slash: PygmalionAI/pygmalion-350m.
function familyOf(model) {
  const owner = (model.repo_id || '').split('/')[0];
  return owner || 'Other';
}

// The list arrives smallest first. Walk it once so each family keeps that order,
// and a family appears when its smallest model does.
function families(models) {
  const groups = [];
  for (const model of models) {
    const name = familyOf(model);
    const group = groups.find((item) => item.name === name);
    if (group) group.models.push(model);
    else groups.push({ name, models: [model] });
  }
  return groups;
}

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
      {families(models).map((group) => (
        <div key={group.name}>
          <div className={bar.group}>{group.name}</div>
          <div className={bar.nest}>
            {group.models.map((model) => {
              const to = manage ? `/model/${model.id}` : `/?model=${model.id}`;
              const active = String(model.id) === String(selected);
              return (
                <NavLink key={model.id} to={to} className={active ? `${bar.link} ${bar.linkActive}` : bar.link}>
                  <span className={bar.linkName}>{model.name}</span>
                  <span className={bar.linkMeta}>{model.parameters ? `${model.parameters} · ` : ''}{model.state === 'ready' ? 'loaded' : model.download_state === 'downloading' ? `${model.download_percent || 0}%` : model.state}</span>
                  {model.download_state === 'downloading' && (
                    <span className={bar.meter} aria-hidden="true">
                      <span className={bar.meterFill} style={{ width: `${model.download_percent || 0}%` }} />
                    </span>
                  )}
                </NavLink>
              );
            })}
          </div>
        </div>
      ))}
      {error && <div className={bar.offline}>{error}</div>}
    </aside>
  );
}
