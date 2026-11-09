import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { deleteSoul, getSoul, saveSoul } from '../api/forge';
import { announceSoulChange } from '../persona/store';
import styles from '../components/Section.module.css';

export default function Figure({ base = '/figures' }) {
  const { soulId } = useParams();
  const navigate = useNavigate();
  const [soul, setSoul] = useState(null);
  const [draft, setDraft] = useState('');
  const [flags, setFlags] = useState('{\n  "USER": "You"\n}');
  const [savedFlags, setSavedFlags] = useState(flags);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let stopped = false;
    setNote('');
    setError('');
    if (!soulId) {
      setSoul(null);
      setDraft('');
      return undefined;
    }
    getSoul(soulId)
      .then((loaded) => {
        if (stopped) return;
        setSoul(loaded);
        setDraft(loaded.content);
        const text = JSON.stringify(loaded.flags && Object.keys(loaded.flags).length ? loaded.flags : { USER: 'You' }, null, 2);
        setFlags(text);
        setSavedFlags(text);
      })
      .catch((err) => {
        if (!stopped) {
          setSoul(null);
          setError(err.message);
        }
      });
    return () => {
      stopped = true;
    };
  }, [soulId]);

  const dirty = soul && (draft !== soul.content || flags !== savedFlags);

  const save = async () => {
    if (!soul || saving) return;
    let parsed;
    try {
      parsed = JSON.parse(flags);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Flags must be a JSON object.');
    } catch (err) {
      setError(err.message);
      return;
    }
    setSaving(true);
    try {
      const saved = await saveSoul(soul.slug, draft, parsed);
      setSoul(saved);
      const text = JSON.stringify(saved.flags || {}, null, 2);
      setFlags(text);
      setSavedFlags(text);
      setNote('Saved.');
      setError('');
      announceSoulChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault();
        save();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const remove = async () => {
    if (!soul || !window.confirm(`Delete ${soul.name}? This removes ${soul.file} and its chats.`)) return;
    try {
      await deleteSoul(soul.slug);
      announceSoulChange();
      navigate(base);
    } catch (err) {
      setError(err.message);
    }
  };

  const test = async () => {
    if (dirty) await save();
    navigate(`/?soul=${soul.slug}`);
  };

  return (
    <div className={styles.page}>
      <h1 className="page__title">{soul?.name || 'Figures'}</h1>
      {!soul && !error && (
        <p className={styles.lead}>
          Each figure is a soul.md you draft. Pick one in the list, or start a new one, then test it in Threads against different models.
        </p>
      )}
      {soul && (
        <section className={`glass glass-panel ${styles.stack}`}>
          <p className={styles.lead}>
            <code>{soul.file}</code> · the heading is the name the model answers to.
          </p>
          <textarea
            className={`field ${styles.editor}`}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setNote('');
            }}
            spellCheck
            aria-label="soul.md"
          />
          <p className={styles.lead}>
            <code>souls/{soul.slug}/flags.json</code> · a reply token like <code>{'<USER>'}</code> is replaced with the value named here.
          </p>
          <textarea
            className="field"
            value={flags}
            onChange={(event) => {
              setFlags(event.target.value);
              setNote('');
            }}
            spellCheck={false}
            aria-label="flags.json"
            rows={6}
          />
          <div className={styles.actions}>
            <button type="button" className="btn btn--sm" onClick={save} disabled={!dirty || saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className="btn btn--sm" onClick={test}>Test in chat</button>
            <button type="button" className="btn btn--sm btn--ghost" onClick={remove}>Delete</button>
            {dirty && !note && <span className={styles.note}>Unsaved changes · ⌘S to save</span>}
            {note && <span className={styles.note}>{note}</span>}
            {error && <span className={styles.noteError}>{error}</span>}
          </div>
        </section>
      )}
      {error && !soul && <p className={styles.noteError}>{error}</p>}
    </div>
  );
}
