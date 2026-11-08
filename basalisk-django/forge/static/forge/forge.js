(() => {
  'use strict';

  const API = '/api/forge';
  const TEXT_FIELDS = ['name', 'epithet', 'personality', 'appearance', 'scenario', 'speaking_style', 'greeting', 'example_dialogue'];
  const AXES = [
    { key: 'warmth', low: 'Reserved', high: 'Warm' },
    { key: 'playfulness', low: 'Serious', high: 'Playful' },
    { key: 'curiosity', low: 'Content', high: 'Curious' },
    { key: 'boldness', low: 'Gentle', high: 'Bold' },
  ];
  // Each part warms the ivory equally; the hint names the first part still missing.
  const PARTS = [
    { done: (p) => p.name.trim(), hint: 'Name her to begin.' },
    { done: (p) => p.personality.trim() || p.traits.length, hint: 'Give her a soul: traits or personality.' },
    { done: (p) => p.appearance.trim(), hint: 'Describe her form.' },
    { done: (p) => p.scenario.trim(), hint: 'Set a scenario.' },
    { done: (p) => p.speaking_style.trim(), hint: 'Describe how she speaks.' },
    { done: (p) => p.greeting.trim(), hint: 'Write her first line.' },
    { done: (p) => p.example_dialogue.trim(), hint: 'Add example dialogue.' },
  ];

  const $ = (id) => document.getElementById(id);
  const form = $('persona-form');
  const els = {
    list: $('figure-list'),
    empty: $('figure-empty'),
    newFigure: $('new-figure'),
    traitList: $('trait-list'),
    traitInput: $('trait-input'),
    temperament: $('temperament'),
    save: $('save-figure'),
    del: $('delete-figure'),
    saveNote: $('save-note'),
    blockStone: document.querySelector('.block-stone'),
    blockName: $('block-name'),
    blockEpithet: $('block-epithet'),
    warmth: $('warmth-readout'),
    warmthHint: $('warmth-hint'),
    status: $('model-status'),
    statusText: $('model-status-text'),
    gate: $('model-gate'),
    gateText: $('model-gate-text'),
    loadModel: $('load-model'),
    transcript: $('transcript'),
    speakForm: $('speak-form'),
    speakInput: $('speak-input'),
    speakSend: $('speak-send'),
    speakClear: $('speak-clear'),
    sampling: document.querySelector('.sampling'),
    mold: $('mold'),
    moldTokens: $('mold-tokens'),
    tabs: [$('tab-speak'), $('tab-mold')],
  };

  const state = {
    personas: [],
    currentId: null,
    draft: blankPersona(),
    dirty: false,
    histories: new Map(),
    model: null,
    pollTimer: null,
    moldTimer: null,
    speaking: false,
  };

  function blankPersona() {
    return {
      name: '', epithet: '', traits: [],
      temperament: Object.fromEntries(AXES.map((a) => [a.key, 50])),
      personality: '', appearance: '', scenario: '', speaking_style: '', greeting: '', example_dialogue: '',
    };
  }

  async function api(path, { method = 'GET', body } = {}) {
    const response = await fetch(API + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(describeError(data) || `Request failed (${response.status}).`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  function describeError(data) {
    if (!data) return '';
    if (typeof data.detail === 'string') return data.detail;
    const first = Object.entries(data)[0];
    if (!first) return '';
    const [field, messages] = first;
    if (messages && typeof messages === 'object' && !Array.isArray(messages)) return describeError(messages);
    const message = Array.isArray(messages) ? messages[0] : messages;
    return field === 'non_field_errors' ? message : `${field.replaceAll('_', ' ')}: ${message}`;
  }

  const historyKey = () => state.currentId ?? 'draft';
  const history = () => {
    if (!state.histories.has(historyKey())) state.histories.set(historyKey(), []);
    return state.histories.get(historyKey());
  };

  function samplingValues() {
    const values = {};
    els.sampling.querySelectorAll('input').forEach((input) => {
      values[input.name] = Number(input.value);
    });
    return values;
  }

  function personaPayload() {
    const { id, created_at, updated_at, ...persona } = state.draft;
    return persona;
  }

  /* Figures list */

  function renderList() {
    els.list.replaceChildren();
    els.empty.hidden = state.personas.length > 0;
    for (const persona of state.personas) {
      const item = document.createElement('li');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'figure-button';
      if (persona.id === state.currentId) button.setAttribute('aria-current', 'true');
      const name = document.createElement('span');
      name.className = 'figure-name';
      name.textContent = persona.name;
      const epithet = document.createElement('span');
      epithet.className = 'figure-epithet';
      epithet.textContent = persona.epithet || 'No epithet';
      button.append(name, epithet);
      button.addEventListener('click', () => openFigure(persona.id));
      item.append(button);
      els.list.append(item);
    }
  }

  function confirmDiscard() {
    return !state.dirty || window.confirm('Discard unsaved changes to this figure?');
  }

  function openFigure(id) {
    if (id === state.currentId || !confirmDiscard()) return;
    const persona = state.personas.find((p) => p.id === id);
    state.currentId = id;
    state.draft = structuredClone({ ...blankPersona(), ...persona });
    state.dirty = false;
    renderAll();
  }

  function newFigure() {
    if (!confirmDiscard()) return;
    state.currentId = null;
    state.draft = blankPersona();
    state.histories.delete('draft');
    state.dirty = false;
    renderAll();
    form.elements.name.focus();
  }

  /* Form */

  function fillForm() {
    for (const field of TEXT_FIELDS) form.elements[field].value = state.draft[field] ?? '';
    form.elements.name.removeAttribute('aria-invalid');
    renderTraits();
    renderTemperament();
    els.del.hidden = state.currentId === null;
    els.saveNote.textContent = '';
  }

  function renderTraits() {
    els.traitList.replaceChildren();
    state.draft.traits.forEach((trait, index) => {
      const item = document.createElement('li');
      item.className = 'trait';
      item.append(trait);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `Remove ${trait}`);
      remove.addEventListener('click', () => {
        state.draft.traits.splice(index, 1);
        changed();
        renderTraits();
        els.traitInput.focus();
      });
      item.append(remove);
      els.traitList.append(item);
    });
  }

  function addTrait(raw) {
    const trait = raw.trim().replace(/,$/, '').trim();
    if (!trait) return;
    const exists = state.draft.traits.some((t) => t.toLowerCase() === trait.toLowerCase());
    if (!exists && state.draft.traits.length < 24) {
      state.draft.traits.push(trait);
      changed();
      renderTraits();
    }
  }

  function renderTemperament() {
    els.temperament.replaceChildren();
    for (const axis of AXES) {
      const row = document.createElement('div');
      row.className = 'axis';
      const low = document.createElement('span');
      low.className = 'axis-low';
      low.textContent = axis.low;
      const slider = document.createElement('input');
      slider.type = 'range';
      slider.min = '0';
      slider.max = '100';
      slider.step = '5';
      slider.value = String(state.draft.temperament?.[axis.key] ?? 50);
      slider.setAttribute('aria-label', `${axis.low} to ${axis.high}`);
      slider.addEventListener('input', () => {
        state.draft.temperament = { ...state.draft.temperament, [axis.key]: Number(slider.value) };
        changed();
      });
      const high = document.createElement('span');
      high.className = 'axis-high';
      high.textContent = axis.high;
      row.append(low, slider, high);
      els.temperament.append(row);
    }
  }

  function changed() {
    state.dirty = true;
    els.saveNote.textContent = 'Unsaved changes';
    renderBlock();
    scheduleMold();
    updateSpeakControls();
  }

  async function saveFigure(event) {
    event.preventDefault();
    if (!state.draft.name.trim()) {
      form.elements.name.setAttribute('aria-invalid', 'true');
      els.saveNote.textContent = 'Name the figure before saving.';
      form.elements.name.focus();
      return;
    }
    els.save.disabled = true;
    els.saveNote.textContent = 'Saving…';
    try {
      const isNew = state.currentId === null;
      const saved = await api(isNew ? '/personas/' : `/personas/${state.currentId}/`, {
        method: isNew ? 'POST' : 'PUT',
        body: personaPayload(),
      });
      if (isNew) {
        state.histories.set(saved.id, state.histories.get('draft') ?? []);
        state.histories.delete('draft');
        state.personas.unshift(saved);
      } else {
        state.personas = [saved, ...state.personas.filter((p) => p.id !== saved.id)];
      }
      state.currentId = saved.id;
      state.draft = structuredClone({ ...blankPersona(), ...saved });
      state.dirty = false;
      renderList();
      els.del.hidden = false;
      els.saveNote.textContent = 'Saved.';
    } catch (error) {
      els.saveNote.textContent = error.message;
    } finally {
      els.save.disabled = false;
    }
  }

  async function deleteFigure() {
    const persona = state.personas.find((p) => p.id === state.currentId);
    if (!persona || !window.confirm(`Delete ${persona.name}? This cannot be undone.`)) return;
    try {
      await api(`/personas/${persona.id}/`, { method: 'DELETE' });
      state.personas = state.personas.filter((p) => p.id !== persona.id);
      state.histories.delete(persona.id);
      state.dirty = false;
      if (state.personas.length) {
        state.currentId = null;
        openFigure(state.personas[0].id);
      } else {
        state.currentId = null;
        state.draft = blankPersona();
        renderAll();
      }
    } catch (error) {
      els.saveNote.textContent = error.message;
    }
  }

  /* The block */

  function renderBlock() {
    const persona = state.draft;
    const done = PARTS.filter((part) => part.done(persona)).length;
    const warmth = done / PARTS.length;
    els.blockStone.style.setProperty('--warmth', warmth.toFixed(3));
    els.blockName.textContent = persona.name.trim() || 'Unnamed';
    els.blockEpithet.textContent = persona.epithet.trim();
    els.warmth.textContent = warmth === 0 ? 'Cold ivory' : warmth === 1 ? 'Warm to the touch' : `Warming · ${Math.round(warmth * 100)}%`;
    const missing = PARTS.find((part) => !part.done(persona));
    els.warmthHint.textContent = missing ? missing.hint : 'Every part is shaped.';
  }

  /* Model */

  function renderModel() {
    const model = state.model;
    if (!model) return;
    els.status.dataset.state = model.state;
    const labels = {
      idle: 'Pygmalion is not loaded',
      loading: 'Loading Pygmalion…',
      ready: `Pygmalion ready on ${model.device}`,
      error: 'Pygmalion failed to load',
      unavailable: 'Model packages not installed',
    };
    els.statusText.textContent = `${labels[model.state] ?? model.state} · ${model.model}`;
    els.status.title = model.detail;

    const needsAction = model.state !== 'ready';
    els.gate.hidden = !needsAction;
    els.gateText.textContent = model.detail;
    els.loadModel.hidden = !['idle', 'error'].includes(model.state);
    els.loadModel.textContent = model.state === 'error' ? 'Try loading again' : 'Load Pygmalion';
    updateSpeakControls();

    clearTimeout(state.pollTimer);
    if (model.state === 'loading') state.pollTimer = setTimeout(refreshModel, 2500);
  }

  async function refreshModel() {
    try {
      state.model = await api('/model/');
    } catch (error) {
      state.model = { state: 'error', model: 'Pygmalion', detail: error.message, device: null };
    }
    renderModel();
  }

  async function loadModel() {
    els.loadModel.disabled = true;
    try {
      state.model = await api('/model/', { method: 'POST' });
    } catch (error) {
      state.model = { ...(state.model ?? {}), state: 'error', detail: error.message };
    } finally {
      els.loadModel.disabled = false;
    }
    renderModel();
  }

  /* Conversation */

  function lineElement(role, text, modifier) {
    const item = document.createElement('li');
    item.className = `line line-${role === 'you' ? 'you' : 'character'}${modifier ? ` line-${modifier}` : ''}`;
    const speaker = document.createElement('span');
    speaker.className = 'line-speaker';
    speaker.textContent = role === 'you' ? 'You' : state.draft.name.trim() || 'Unnamed';
    const body = document.createElement('p');
    body.className = 'line-text';
    body.textContent = text;
    item.append(speaker, body);
    return item;
  }

  function renderTranscript() {
    els.transcript.replaceChildren();
    const greeting = state.draft.greeting.trim();
    if (greeting) els.transcript.append(lineElement('character', fillPlaceholders(greeting)));
    for (const turn of history()) els.transcript.append(lineElement(turn.role, turn.content));
    if (!greeting && !history().length) {
      const empty = document.createElement('li');
      empty.className = 'transcript-empty';
      empty.textContent = 'No conversation yet. Write her a greeting, or say something first.';
      els.transcript.append(empty);
    }
    els.transcript.scrollTop = els.transcript.scrollHeight;
  }

  function fillPlaceholders(text) {
    return text.replaceAll('{{char}}', state.draft.name.trim() || 'Unnamed').replaceAll('{{user}}', 'you');
  }

  function updateSpeakControls() {
    const ready = state.model?.state === 'ready';
    const named = Boolean(state.draft.name.trim());
    els.speakSend.disabled = state.speaking || !ready || !named;
    els.speakSend.title = !named ? 'Name the figure first.' : !ready ? 'Load Pygmalion first.' : '';
  }

  async function speak(event) {
    event.preventDefault();
    const message = els.speakInput.value.trim();
    if (!message || els.speakSend.disabled) return;

    const turns = history();
    turns.push({ role: 'you', content: message });
    els.speakInput.value = '';
    renderTranscript();
    const pending = lineElement('character', 'Thinking…', 'pending');
    els.transcript.append(pending);
    els.transcript.scrollTop = els.transcript.scrollHeight;

    state.speaking = true;
    updateSpeakControls();
    try {
      const result = await api('/speak/', {
        method: 'POST',
        body: { persona: personaPayload(), history: turns, sampling: samplingValues() },
      });
      turns.push({ role: 'character', content: result.reply || '…' });
      renderTranscript();
    } catch (error) {
      turns.pop();
      els.speakInput.value = message;
      renderTranscript();
      els.transcript.append(lineElement('character', error.message, 'error'));
      if (error.data?.model) {
        state.model = error.data.model;
        renderModel();
      }
    } finally {
      state.speaking = false;
      updateSpeakControls();
      scheduleMold();
    }
  }

  function clearConversation() {
    state.histories.set(historyKey(), []);
    renderTranscript();
    scheduleMold();
  }

  /* Mold */

  function scheduleMold() {
    clearTimeout(state.moldTimer);
    state.moldTimer = setTimeout(refreshMold, 300);
  }

  async function refreshMold() {
    if (!state.draft.name.trim()) {
      els.mold.textContent = 'Name the figure to see the prompt.';
      els.moldTokens.textContent = '';
      return;
    }
    try {
      const result = await api('/mold/', {
        method: 'POST',
        body: { persona: personaPayload(), history: history(), sampling: samplingValues() },
      });
      els.mold.textContent = result.prompt;
      els.moldTokens.textContent = `About ${result.tokens} tokens.`;
    } catch (error) {
      els.mold.textContent = error.message;
      els.moldTokens.textContent = '';
    }
  }

  /* Tabs */

  function selectTab(tab) {
    for (const t of els.tabs) {
      const selected = t === tab;
      t.setAttribute('aria-selected', String(selected));
      t.tabIndex = selected ? 0 : -1;
      $(t.getAttribute('aria-controls')).hidden = !selected;
    }
    tab.focus();
  }

  /* Wiring */

  function renderAll() {
    renderList();
    fillForm();
    renderBlock();
    renderTranscript();
    updateSpeakControls();
    scheduleMold();
  }

  form.addEventListener('input', (event) => {
    const field = event.target.name;
    if (!TEXT_FIELDS.includes(field)) return;
    state.draft[field] = event.target.value;
    if (field === 'name') event.target.removeAttribute('aria-invalid');
    changed();
    if (field === 'greeting' || field === 'name') renderTranscript();
  });
  form.addEventListener('submit', saveFigure);
  els.del.addEventListener('click', deleteFigure);
  els.newFigure.addEventListener('click', newFigure);

  els.traitInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      addTrait(els.traitInput.value);
      els.traitInput.value = '';
    } else if (event.key === 'Backspace' && !els.traitInput.value && state.draft.traits.length) {
      state.draft.traits.pop();
      changed();
      renderTraits();
    }
  });
  els.traitInput.addEventListener('blur', () => {
    addTrait(els.traitInput.value);
    els.traitInput.value = '';
  });

  els.speakForm.addEventListener('submit', speak);
  els.speakInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      els.speakForm.requestSubmit();
    }
  });
  els.speakClear.addEventListener('click', clearConversation);
  els.loadModel.addEventListener('click', loadModel);
  els.sampling.addEventListener('change', scheduleMold);

  els.tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      const step = event.key === 'ArrowRight' ? 1 : -1;
      selectTab(els.tabs[(index + step + els.tabs.length) % els.tabs.length]);
    });
  });

  window.addEventListener('beforeunload', (event) => {
    if (state.dirty) event.preventDefault();
  });

  async function start() {
    renderAll();
    refreshModel();
    try {
      state.personas = await api('/personas/');
      if (state.personas.length) openFigure(state.personas[0].id);
      else renderList();
    } catch (error) {
      els.empty.hidden = false;
      els.empty.textContent = `Could not load figures: ${error.message}`;
    }
  }

  start();
})();
