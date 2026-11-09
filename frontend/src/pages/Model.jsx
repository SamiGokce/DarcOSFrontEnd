import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { createModel, downloadModel, listModels, loadRegisteredModel, saveHuggingFaceToken, uninstallModel } from '../api/forge';
import styles from '../components/Section.module.css';

const DEFAULTS = { max_new_tokens: 48, temperature: 0.7, top_p: 0.9, repetition_penalty: 1.15 };
const STORAGE_KEY = 'basalisk.modelSampling';

const FIELDS = [
  ['max_new_tokens', 'Max new tokens', 1, 512, 1],
  ['temperature', 'Temperature', 0, 2, 0.05],
  ['top_p', 'Top p', 0.05, 1, 0.05],
  ['repetition_penalty', 'Repetition penalty', 1, 2, 0.05],
];

const DOWNLOADS = [
  { name: 'Pygmalion 350M', repo_id: 'PygmalionAI/pygmalion-350m', parameters: '350M', context_tokens: 2048 },
  { name: 'Pygmalion 1.3B', repo_id: 'PygmalionAI/pygmalion-1.3b', parameters: '1.3B', context_tokens: 2048 },
  { name: 'Pygmalion 2.7B', repo_id: 'PygmalionAI/pygmalion-2.7b', parameters: '2.7B', context_tokens: 2048 },
  { name: 'Pygmalion 6B', repo_id: 'PygmalionAI/pygmalion-6b', parameters: '6B', context_tokens: 2048 },
  { name: 'Pygmalion 2 7B', repo_id: 'PygmalionAI/pygmalion-2-7b', parameters: '7B', context_tokens: 4096 },
  { name: 'Pygmalion 2 13B', repo_id: 'PygmalionAI/pygmalion-2-13b', parameters: '13B', context_tokens: 4096 },
];

function readSampling() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') };
  } catch {
    return { ...DEFAULTS };
  }
}

export default function Model() {
  const { modelId } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [shelf, setShelf] = useState(null);
  const [pick, setPick] = useState(DOWNLOADS[0].repo_id);
  const [sampling, setSampling] = useState(readSampling);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [token, setToken] = useState('');

  useEffect(() => {
    if (!modelId) {
      setRecord(null);
      let stopped = false;
      listModels()
        .then((rows) => {
          if (!stopped) setShelf(rows);
        })
        .catch((err) => {
          if (!stopped) setError(err.message);
        });
      return () => {
        stopped = true;
      };
    }
    let stopped = false;
    const read = () =>
      listModels()
        .then((rows) => {
          if (stopped) return;
          setRecord(rows.find((row) => String(row.id) === String(modelId)) || null);
        })
        .catch((err) => {
          if (!stopped) setError(err.message);
        });
    read();
    const id = setInterval(read, 400);
    return () => {
      stopped = true;
      clearInterval(id);
    };
  }, [modelId]);

  const choices = DOWNLOADS.filter((item) => !(shelf || []).some((row) => row.repo_id === item.repo_id));
  const chosen = choices.find((item) => item.repo_id === pick) || choices[0] || null;

  const add = async (event) => {
    event.preventDefault();
    if (!chosen) return;
    try {
      const saved = await createModel({
        name: chosen.name,
        repo_id: chosen.repo_id,
        parameters: chosen.parameters,
        context_tokens: chosen.context_tokens,
        notes: '',
      });
      setError('');
      navigate(`/model/${saved.id}`);
    } catch (err) {
      setError(err.message);
    }
  };

  const run = async (action) => {
    try {
      setNote('');
      const result = action === 'download' ? await downloadModel(record.id) : await loadRegisteredModel(record.id);
      if (result && result.id) setRecord((current) => ({ ...current, ...result }));
      setNote(action === 'load' ? (result.detail || '') : '');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const saveToken = async (event) => {
    event.preventDefault();
    const value = token.trim();
    if (!value) return;
    try {
      await saveHuggingFaceToken(value);
      setToken('');
      const result = await downloadModel(record.id);
      if (result && result.id) setRecord((current) => ({ ...current, ...result }));
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const uninstall = async () => {
    if (!window.confirm(`Remove the downloaded weights for ${record.name}?`)) return;
    try {
      const result = await uninstallModel(record.id);
      if (result && result.id) setRecord((current) => ({ ...current, ...result }));
      setNote('');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const changeSampling = (key, value) => {
    const next = { ...sampling, [key]: Number(value) };
    setSampling(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const state = record?.state || 'catalog';
  const dotClass = state === 'ready' ? styles.dotReady : state === 'downloaded' ? styles.dotDownloaded : state === 'loading' || state === 'downloading' ? styles.dotLoading : state === 'error' ? styles.dotError : '';
  const loading = state === 'loading';
  const downloaded = record?.download_state === 'downloaded';
  const downloading = record?.download_state === 'downloading';

  return (
    <div className={styles.page}>
      <h1 className="page__title">{record ? record.name : 'New model'}</h1>
      {!record && (
        <form className={`glass glass-panel ${styles.stack}`} onSubmit={add}>
          <p className={styles.lead}>Pick a model to add. Name, repository, and parameters come from the choice.</p>
          {choices.length === 0 && shelf && <p className={styles.lead}>Every model in the list is already on the shelf.</p>}
          {chosen && (
            <>
              <label className={styles.fieldLabel}>
                Model
                <select className="field" value={chosen.repo_id} onChange={(event) => setPick(event.target.value)}>
                  {choices.map((item) => (
                    <option key={item.repo_id} value={item.repo_id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <p className={styles.lead}>Name: {chosen.name}</p>
              <p className={styles.lead}>Repository: {chosen.repo_id}</p>
              <p className={styles.lead}>Parameters: {chosen.parameters}</p>
            </>
          )}
          <div className={styles.actions}>
            <button type="submit" className="btn btn--sm" disabled={!chosen}>Add model</button>
            {error && <span className={styles.noteError}>{error}</span>}
          </div>
        </form>
      )}
      {record && (
        <>
          <section className={`glass glass-panel ${styles.stack}`}>
            <p className={styles.status}>
              <span className={`${styles.dot} ${dotClass}`} />
              <span>{record.detail}</span>
            </p>
            {loading && (
              <div className={styles.meterRow}>
                <div className={`${styles.meter} ${styles.meterLoad}`} role="progressbar" aria-label="Loading" aria-busy="true">
                  <div className={styles.meterFill} />
                </div>
              </div>
            )}
            {downloading && (
              <div className={styles.meterRow}>
                <div
                  className={styles.meter}
                  role="progressbar"
                  aria-label="Download"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={record.download_percent || 0}
                >
                  <div className={styles.meterFill} style={{ width: `${record.download_percent || 0}%` }} />
                </div>
                <span className={styles.note}>{record.download_percent || 0}%</span>
              </div>
            )}
            <p className={styles.lead}>Repository: {record.repo_id || 'not set yet'}</p>
            <p className={styles.lead}>Parameters: {record.parameters || 'unknown'}</p>
            <p className={styles.lead}>Context: {record.context_tokens} tokens{record.device ? ` · ${record.device}` : ''}</p>
            {record.notes && <p className={styles.lead}>{record.notes}</p>}
            {record.download_needs_token && (
              <form className={styles.stack} onSubmit={saveToken}>
                <p className={styles.noteError}>Log in to Hugging Face and paste an access token.</p>
                <a href="https://huggingface.co/settings/tokens" target="_blank" rel="noreferrer">huggingface.co/settings/tokens</a>
                <input
                  className="field"
                  type="password"
                  autoComplete="off"
                  aria-label="Hugging Face token"
                  placeholder="hf_…"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
                <button type="submit" className="btn btn--sm" disabled={!token.trim()}>Save token</button>
              </form>
            )}
            <div className={styles.actions}>
              {downloaded ? (
                <>
                  <button type="button" className="btn btn--sm" onClick={() => run('load')} disabled={loading}>Load</button>
                  <button type="button" className="btn btn--sm btn--ghost" onClick={uninstall}>Uninstall</button>
                </>
              ) : (
                <button type="button" className="btn btn--sm" onClick={() => run('download')} disabled={downloading}>Download</button>
              )}
              {note && <span className={styles.note}>{note}</span>}
              {error && <span className={styles.noteError}>{error}</span>}
            </div>
          </section>
          <section className={`glass glass-panel ${styles.stack}`}>
            <h2 className="glass-panel__title">Sampling</h2>
            <p className={styles.lead}>Used when this chat replies. Saved in this browser.</p>
            <div className={styles.grid}>
              {FIELDS.map(([key, label, min, max, step]) => (
                <label key={key} className={styles.fieldLabel}>
                  {label}
                  <input className="field" type="number" min={min} max={max} step={step} value={sampling[key]} onChange={(event) => changeSampling(key, event.target.value)} />
                </label>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
