from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from . import downloads
from .llm import engine
from .prompt import build_prompt, clean_reply, persona_text

PERSONA = {
    'name': 'Galatea',
    'epithet': 'an ivory statue, newly alive',
    'traits': ['candid'],
    'temperament': {'warmth': 90, 'playfulness': 50, 'curiosity': 70, 'boldness': 10},
    'personality': 'She asks many questions.',
    'scenario': "{{char}} meets {{user}} in the workshop.",
    'greeting': 'Who are you?',
    'example_dialogue': '{{user}}: Hello.\n{{char}}: Hello. Is that a greeting?',
}


class PromptTests(TestCase):
    def test_persona_text_turns_temperament_into_words(self):
        text = persona_text(PERSONA)
        self.assertIn('Galatea is an ivory statue, newly alive.', text)
        self.assertIn('Galatea is very warm, curious, very gentle, and candid.', text)
        self.assertIn('She asks many questions.', text)

    def test_build_prompt_uses_pygmalion_format(self):
        prompt = build_prompt(PERSONA, [{'role': 'you', 'content': 'A visitor.'}])
        self.assertEqual(prompt.splitlines(), [
            "Galatea's Persona: " + persona_text(PERSONA),
            'Scenario: Galatea meets you in the workshop.',
            '<START>',
            'You: Hello.',
            'Galatea: Hello. Is that a greeting?',
            '<START>',
            'Galatea: Who are you?',
            'You: A visitor.',
            'Galatea:',
        ])

    def test_build_prompt_drops_oldest_turns_to_fit(self):
        history = [{'role': 'you', 'content': f'message {i} ' + 'x' * 200} for i in range(20)]
        prompt = build_prompt(PERSONA, history, count_tokens=len, budget=1500)
        self.assertLessEqual(len(prompt), 1500)
        self.assertIn('message 19', prompt)
        self.assertNotIn('message 0 ', prompt)

    def test_clean_reply_stops_at_the_next_speaker(self):
        raw = ' I am Galatea. *smiles*\nYou: And I am you.\nGalatea: Indeed.'
        self.assertEqual(clean_reply(raw, 'Galatea'), 'I am Galatea. *smiles*')


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_seeded_galatea_is_listed(self):
        names = [p['name'] for p in self.client.get('/api/forge/personas/').json()]
        self.assertIn('Galatea', names)

    def test_create_requires_a_name(self):
        response = self.client.post('/api/forge/personas/', {'name': '  '}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_temperament_is_clamped(self):
        response = self.client.post(
            '/api/forge/personas/', {'name': 'Echo', 'temperament': {'warmth': 400}}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['temperament']['warmth'], 100)

    def test_mold_previews_an_unsaved_draft(self):
        response = self.client.post('/api/forge/mold/', {'persona': PERSONA, 'history': []}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['prompt'].endswith('Galatea: Who are you?\nGalatea:'))

    def test_speak_is_refused_until_the_model_is_loaded(self):
        body = {'persona': PERSONA, 'history': [{'role': 'you', 'content': 'Hi'}]}
        response = self.client.post('/api/forge/speak/', body, format='json')
        self.assertEqual(response.status_code, 409)

    def test_speak_returns_the_cleaned_reply(self):
        body = {'persona': PERSONA, 'history': [{'role': 'you', 'content': 'Hi'}]}
        with mock.patch.object(engine, 'state', 'ready'), \
                mock.patch.object(engine, 'generate', return_value=' Hello!\nYou: more'):
            response = self.client.post('/api/forge/speak/', body, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], 'Hello!')


class DownloadTests(TestCase):
    def setUp(self):
        downloads.reset()
        self.client = APIClient()

    def test_progress_hook_uses_the_tqdm_module(self):
        import sys
        import huggingface_hub.utils.tqdm  # noqa: F401

        module = sys.modules['huggingface_hub.utils.tqdm']
        self.assertTrue(isinstance(module.tqdm, type))

    def test_progress_tracks_bytes(self):
        with downloads._lock:
            downloads._jobs['org/model'] = downloads._view('downloading', 0, 0, 0, 'Checking files…', 'org/model')
        downloads.note_size('org/model', 1000, 0)
        downloads.add_bytes('org/model', 250)
        snap = downloads.snapshot('org/model')
        self.assertEqual(snap['percent'], 25)
        self.assertEqual(snap['detail'], 'Downloading… 250 B of 1000 B')
        downloads.finish('org/model')
        self.assertEqual(downloads.snapshot('org/model')['state'], 'downloaded')
        self.assertEqual(downloads.snapshot('org/model')['percent'], 100)

    def test_download_reports_percent(self):
        created = self.client.post(
            '/api/forge/models/',
            {'name': 'Tiny', 'repo_id': 'example/missing-model', 'parameters': '1M', 'context_tokens': 128},
            format='json',
        )
        self.assertEqual(created.status_code, 201)
        model_id = created.json()['id']
        with mock.patch('forge.downloads._run'):
            response = self.client.post(f'/api/forge/models/{model_id}/download/')
        body = response.json()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(body['download_state'], 'downloading')
        self.assertEqual(body['download_percent'], 0)
        self.assertEqual(body['state'], 'downloading')

    def test_a_second_download_is_refused(self):
        first = self.client.post(
            '/api/forge/models/',
            {'name': 'One', 'repo_id': 'example/one', 'parameters': '1M'},
            format='json',
        ).json()['id']
        second = self.client.post(
            '/api/forge/models/',
            {'name': 'Two', 'repo_id': 'example/two', 'parameters': '1M'},
            format='json',
        ).json()['id']
        with mock.patch('forge.downloads._run'):
            self.client.post(f'/api/forge/models/{first}/download/')
            response = self.client.post(f'/api/forge/models/{second}/download/')
        self.assertEqual(response.status_code, 409)
