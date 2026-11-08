export const AXES = [
  ['warmth', 'Reserved', 'Warm'],
  ['playfulness', 'Serious', 'Playful'],
  ['curiosity', 'Content', 'Curious'],
  ['boldness', 'Gentle', 'Bold'],
];

export const blankPersona = () => ({
  name: '',
  epithet: '',
  traits: [],
  temperament: { warmth: 50, playfulness: 50, curiosity: 50, boldness: 50 },
  personality: '',
  appearance: '',
  scenario: '',
  speaking_style: '',
  greeting: '',
  example_dialogue: '',
});

export const FACETS = {
  name: {
    title: 'Name',
    fields: [
      { key: 'name', label: 'Name' },
      { key: 'epithet', label: 'Epithet', hint: 'Completes the sentence “she is …”.' },
    ],
  },
  soul: {
    title: 'Soul',
    traits: true,
    temperament: true,
    fields: [{ key: 'personality', label: 'Personality', area: true, rows: 5 }],
  },
  form: {
    title: 'Form',
    fields: [{ key: 'appearance', label: 'Appearance', area: true, rows: 5, hint: 'How she looks and moves.' }],
  },
  world: {
    title: 'World',
    fields: [{
      key: 'scenario',
      label: 'Scenario',
      area: true,
      rows: 5,
      hint: 'Use {{user}} for you and {{char}} for her name.',
    }],
  },
  voice: {
    title: 'Voice',
    fields: [
      { key: 'speaking_style', label: 'Speaking style', area: true, rows: 3 },
      { key: 'greeting', label: 'Greeting', area: true, rows: 3, hint: 'Her first line when a conversation starts.' },
      { key: 'example_dialogue', label: 'Example dialogue', area: true, rows: 6, hint: 'One line per turn. Teaches the model her voice.' },
    ],
  },
};

export const PERSONA_SECTIONS = ['figures', 'name', 'soul', 'form', 'world', 'voice', 'speak', 'mold'];

const histories = new Map();

export function historyFor(id) {
  const key = id ?? 'new';
  if (!histories.has(key)) histories.set(key, []);
  return histories.get(key);
}
