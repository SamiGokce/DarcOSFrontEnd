import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { deletePersona, getPersona, moldPrompt, speak, updatePersona } from '../api/forge';
import { AXES, blankPersona, historyFor } from '../persona/store';
import styles from '../components/Section.module.css';

const STORAGE_KEY = 'basalisk.modelSampling';

function readSampling() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function personaBody(persona, traitsText) {
  const body = {
    ...persona,
    traits: traitsText.split(',').map((trait) => trait.trim()).filter(Boolean),
  };
  delete body.id;
  delete body.created_at;
  delete body.updated_at;
  return body;
}

export default function Figure({ base = '/figures' }) {
  const { personaId } = useParams();
  const navigate = useNavigate();
  const [draft, setDraft] = useState(null);
  const [traitsText, setTraitsText] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [turns, setTurns] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [tokens, setTokens] = useState(null);

  useEffect(() => {
    let stopped = false;
    setNote('');
    setError('');
    setMessage('');
    if (!personaId) {
      setDraft(null);
      setTurns([]);
      setPrompt('');
      setTokens(null);
      return undefined;
    }
    getPersona(personaId)
      .then(async (persona) => {
        if (stopped) return;
        const next = { ...blankPersona(), ...persona };
        const traits = (persona.traits || []).join(', ');
        setDraft(next);
        setTraitsText(traits);
        setTurns(historyFor(persona.id).slice());
        try {
          const cast = await moldPrompt({ persona: personaBody(next, traits), history: historyFor(persona.id) });
          if (!stopped) {
            setPrompt(cast.prompt);
            setTokens(cast.tokens);
          }
        } catch (err) {
          if (!stopped) setError(err.message);
        }
      })
      .catch((err) => {
        if (!stopped) setError(err.message);
      });
    return () => {
      stopped = true;
    };
  }, [personaId]);

  const setField = (field, value) => setDraft((current) => ({ ...current, [field]: value }));

  const save = async (event) => {
    event.preventDefault();
    if (!draft?.name.trim()) {
      setError('Give the figure a name.');
      return;
    }
    try {
      const saved = await updatePersona(draft.id, personaBody(draft, traitsText));
      const next = { ...blankPersona(), ...saved };
      setDraft(next);
      setNote('Saved.');
      setError('');
      const cast = await moldPrompt({ persona: personaBody(next, (saved.traits || []).join(', ')), history: historyFor(saved.id) });
      setPrompt(cast.prompt);
      setTokens(cast.tokens);
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async () => {
    if (!draft?.id || !window.confirm(`Delete ${draft.name}?`)) return;
    try {
      await deletePersona(draft.id);
      navigate(base);
    } catch (err) {
      setError(err.message);
    }
  };

  const send = async (event) => {
    event.preventDefault();
    const text = message.trim();
    if (!text || !draft || busy) return;
    const history = historyFor(draft.id);
    history.push({ role: 'you', content: text });
    setTurns(history.slice());
    setMessage('');
    setBusy(true);
    setError('');
    try {
      const result = await speak({ persona: personaBody(draft, traitsText), history, sampling: readSampling() });
      history.push({ role: 'character', content: result.reply });
      setTurns(history.slice());
      const cast = await moldPrompt({ persona: personaBody(draft, traitsText), history });
      setPrompt(cast.prompt);
      setTokens(cast.tokens);
    } catch (err) {
      history.pop();
      setTurns(history.slice());
      setMessage(text);
      setError(err.message === 'Not loaded.' ? 'Pygmalion is not loaded yet. Load it from Model.' : err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1 className="page__title">{draft?.name || 'Figure'}</h1>
      {!draft && <p className={styles.lead}>Pick a figure in the list, or start a new one.</p>}
      {draft && (
        <>
          <form className={styles.form} onSubmit={save}>
            <section className={`glass glass-panel ${styles.stack}`}>
              <h2 className="glass-panel__title">Name</h2>
              <label className={styles.fieldLabel}>
                Name
                <input className="field" value={draft.name} onChange={(event) => setField('name', event.target.value)} />
              </label>
              <label className={styles.fieldLabel}>
                Epithet
                <input className="field" value={draft.epithet} onChange={(event) => setField('epithet', event.target.value)} />
                <span className={styles.note}>Completes the sentence “she is …”.</span>
              </label>
            </section>

            <section className={`glass glass-panel ${styles.stack}`}>
              <h2 className="glass-panel__title">Soul</h2>
              <label className={styles.fieldLabel}>
                Traits
                <input className="field" value={traitsText} onChange={(event) => setTraitsText(event.target.value)} placeholder="ivory, curious, gentle" />
              </label>
              {AXES.map(([key, low, high]) => (
                <label key={key} className={styles.fieldLabel}>
                  {low} — {high}
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={draft.temperament[key]}
                    onChange={(event) => setField('temperament', { ...draft.temperament, [key]: Number(event.target.value) })}
                  />
                </label>
              ))}
              <label className={styles.fieldLabel}>
                Personality
                <textarea className="field" rows={5} value={draft.personality} onChange={(event) => setField('personality', event.target.value)} />
              </label>
            </section>

            <section className={`glass glass-panel ${styles.stack}`}>
              <h2 className="glass-panel__title">Form</h2>
              <label className={styles.fieldLabel}>
                Appearance
                <textarea className="field" rows={4} value={draft.appearance} onChange={(event) => setField('appearance', event.target.value)} />
                <span className={styles.note}>How she looks and moves.</span>
              </label>
            </section>

            <section className={`glass glass-panel ${styles.stack}`}>
              <h2 className="glass-panel__title">World</h2>
              <label className={styles.fieldLabel}>
                Scenario
                <textarea className="field" rows={4} value={draft.scenario} onChange={(event) => setField('scenario', event.target.value)} />
                <span className={styles.note}>Use {'{{user}}'} for you and {'{{char}}'} for her name.</span>
              </label>
            </section>

            <section className={`glass glass-panel ${styles.stack}`}>
              <h2 className="glass-panel__title">Voice</h2>
              <label className={styles.fieldLabel}>
                Speaking style
                <textarea className="field" rows={3} value={draft.speaking_style} onChange={(event) => setField('speaking_style', event.target.value)} />
              </label>
              <label className={styles.fieldLabel}>
                Greeting
                <textarea className="field" rows={3} value={draft.greeting} onChange={(event) => setField('greeting', event.target.value)} />
                <span className={styles.note}>Her first line when a conversation starts.</span>
              </label>
              <label className={styles.fieldLabel}>
                Example dialogue
                <textarea className="field" rows={6} value={draft.example_dialogue} onChange={(event) => setField('example_dialogue', event.target.value)} />
                <span className={styles.note}>One line per turn. Teaches the model her voice.</span>
              </label>
            </section>

            <div className={styles.actions}>
              <button type="submit" className="btn btn--sm">Save</button>
              <button type="button" className="btn btn--sm btn--ghost" onClick={remove}>Delete</button>
              {note && <span className={styles.note}>{note}</span>}
              {error && <span className={styles.noteError}>{error}</span>}
            </div>
          </form>

          <section className={`glass glass-panel ${styles.stack}`}>
            <h2 className="glass-panel__title">Speak</h2>
            {draft.greeting && turns.length === 0 && (
              <div className="history-item"><strong>{draft.name}</strong> {draft.greeting}</div>
            )}
            {turns.map((turn, index) => (
              <div key={index} className="history-item">
                <strong>{turn.role === 'you' ? 'You' : draft.name}</strong> {turn.content}
              </div>
            ))}
            {turns.length === 0 && !draft.greeting && <div className="history-item">No lines yet.</div>}
            <form className={styles.actions} onSubmit={send}>
              <input className="field" value={message} onChange={(event) => setMessage(event.target.value)} placeholder={`Say something to ${draft.name}`} disabled={busy} />
              <button type="submit" className="btn btn--sm" disabled={busy}>{busy ? 'Writing…' : 'Send'}</button>
            </form>
          </section>

          <section className={`glass glass-panel ${styles.stack}`}>
            <h2 className="glass-panel__title">Mold</h2>
            <p className={styles.lead}>{tokens == null ? 'Casting the prompt…' : `${tokens} tokens, including the conversation so far.`}</p>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.82rem', margin: 0 }}>{prompt}</pre>
          </section>
        </>
      )}
      {error && !draft && <p className={styles.noteError}>{error}</p>}
    </div>
  );
}
