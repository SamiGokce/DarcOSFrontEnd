import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { deleteSoul, getSoul, listMemories, saveSoul } from '../api/forge';
import { announceSoulChange } from '../persona/store';
import Markdown from '../components/Markdown';
import styles from '../components/Section.module.css';

export default function Figure({ base = '/figures' }) {
  const { soulId } = useParams();
  const navigate = useNavigate();
  const [soul, setSoul] = useState(null);
  const [draft, setDraft] = useState('');
  const [flags, setFlags] = useState('{\n  "USER": "You"\n}');
  const [savedFlags, setSavedFlags] = useState(flags);
  const [person, setPerson] = useState(null);
  const [savedPerson, setSavedPerson] = useState('');
  const [memories, setMemories] = useState([]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    let stopped = false;
    setNote('');
    setError('');
    setMemories([]);
    if (!soulId) {
      setSoul(null);
      setDraft('');
      return undefined;
    }
    getSoul(soulId)
      .then((loaded) => {
        if (stopped) return;
        setSoul(loaded);
        listMemories(soulId).then((rows) => {
          if (!stopped) setMemories(rows);
        }).catch(() => {
          if (!stopped) setMemories([]);
        });
        setDraft(loaded.content);
        const text = JSON.stringify(loaded.flags && Object.keys(loaded.flags).length ? loaded.flags : { USER: 'You' }, null, 2);
        setFlags(text);
        setSavedFlags(text);
        setPerson(loaded.person || {});
        setSavedPerson(JSON.stringify(loaded.person || {}));
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

  const dirty = soul && (draft !== soul.content || flags !== savedFlags || JSON.stringify(person) !== savedPerson);

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
      const saved = await saveSoul(soul.slug, draft, parsed, person);
      setSoul(saved);
      const text = JSON.stringify(saved.flags || {}, null, 2);
      setFlags(text);
      setSavedFlags(text);
      setPerson(saved.person || {});
      setSavedPerson(JSON.stringify(saved.person || {}));
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

  const choose = (key, value) => {
    setPerson((current) => ({ ...current, [key]: value }));
    setNote('');
  };

  const toggle = (field, option) => {
    setPerson((current) => {
      const selected = new Set(current[field.key] || []);
      if (selected.has(option)) selected.delete(option);
      else selected.add(option);
      return { ...current, [field.key]: field.options.filter((item) => selected.has(item)) };
    });
    setNote('');
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
          Each figure is a written profile you draft. Pick one in the list, or start a new one, then test it in Threads against different models.
        </p>
      )}
      {soul && (
        <section className={`glass glass-panel ${styles.stack}`}>
          <div className={styles.actions}>
            <button
              type="button"
              className={preview ? 'btn btn--sm btn--ghost' : 'btn btn--sm'}
              aria-pressed={!preview}
              onClick={() => setPreview(false)}
            >
              Edit
            </button>
            <button
              type="button"
              className={preview ? 'btn btn--sm' : 'btn btn--sm btn--ghost'}
              aria-pressed={preview}
              onClick={() => setPreview(true)}
            >
              Preview
            </button>
          </div>
          {preview ? (
            <Markdown source={draft} />
          ) : (
            <textarea
              className={`field ${styles.editorFile}`}
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                setNote('');
              }}
              spellCheck
              aria-label="Profile in markdown"
            />
          )}
          <h2 className={styles.sectionTitle}>Person</h2>
          <p className={styles.lead}>General facts about this person. Each one is a choice.</p>
          {person && (
            <>
              <div className={styles.grid}>
                {(soul.person_fields || []).filter((field) => field.kind === 'select').map((field) => (
                  <label key={field.key} className={styles.fieldLabel}>
                    {field.label}
                    <select
                      className={`field ${styles.control}`}
                      value={person[field.key] || ''}
                      onChange={(event) => choose(field.key, event.target.value)}
                    >
                      <option value="">Unspecified</option>
                      {field.options.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              {(soul.person_fields || []).filter((field) => field.kind === 'multi').map((field) => (
                <fieldset key={field.key} className={styles.multi}>
                  <legend>{field.label}</legend>
                  <div className={styles.choices}>
                    {field.options.map((option) => {
                      const on = (person[field.key] || []).includes(option);
                      return (
                        <button
                          key={option}
                          type="button"
                          aria-pressed={on}
                          className={on ? styles.choiceOn : styles.choice}
                          onClick={() => toggle(field, option)}
                        >
                          {option}
                        </button>
                      );
                    })}
                  </div>
                </fieldset>
              ))}
            </>
          )}
          <h2 className={styles.sectionTitle}>Memories</h2>
          <p className={styles.lead}>Every exchange from this figure's chats. A reply recalls the closest ones by meaning.</p>
          {memories.length === 0 ? (
            <p className={styles.lead}>Nothing remembered yet.</p>
          ) : (
            <ul className={styles.memories}>
              {memories.map((memory, index) => (
                <li key={`${memory.chat_id}-${index}`} className={styles.memory}>
                  <span className={styles.meta}>{memory.chat} · {memory.model}</span>
                  <pre className={styles.prompt}>{memory.text}</pre>
                </li>
              ))}
            </ul>
          )}
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
