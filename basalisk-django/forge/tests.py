import os
import json
import re
import tempfile
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from . import downloads, embed, gate, person, prompt, rag, souls
from .llm import engine
from .models import Chat, LanguageModel
from .llm import weights_missing
from .prompt import build_prompt, clean_reply, decode_prompt, is_unfinished, render_reply

SOUL = """# Mira

A lighthouse keeper who talks to ships at night.

## Voice

Short sentences. Dry humour. Never uses exclamation marks.

## History

Her brother sailed north and never wrote back. She keeps his compass on the desk.

## Garden

She grows tomatoes in a cracked bathtub behind the lighthouse.
"""


class SoulDirMixin:
    def setUp(self):
        super().setUp()
        self._souls = tempfile.TemporaryDirectory()
        os.environ['BASALISK_SOULS_DIR'] = self._souls.name

    def tearDown(self):
        os.environ.pop('BASALISK_SOULS_DIR', None)
        self._souls.cleanup()
        super().tearDown()


class SoulStoreTests(SoulDirMixin, TestCase):
    def test_create_writes_a_soul_md_named_after_the_figure(self):
        soul = souls.create('Mira Vale')
        self.assertEqual(soul['slug'], 'mira-vale')
        self.assertEqual(soul['name'], 'Mira Vale')
        path = os.path.join(self._souls.name, 'mira-vale', 'soul.md')
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(soul['content'].startswith('# Mira Vale'))

    def test_the_heading_is_the_name(self):
        soul = souls.create('Draft')
        saved = souls.save(soul['slug'], '# Renamed\n\nBody.')
        self.assertEqual(saved['name'], 'Renamed')
        self.assertEqual([s['name'] for s in souls.list_souls()], ['Renamed'])

    def test_duplicate_names_get_their_own_folder(self):
        self.assertEqual(souls.create('Mira')['slug'], 'mira')
        self.assertEqual(souls.create('Mira')['slug'], 'mira-2')

    def test_slugs_cannot_escape_the_souls_folder(self):
        with self.assertRaises(souls.SoulNotFound):
            souls.get('../etc')

    def test_no_figure_is_seeded(self):
        self.assertEqual(souls.list_souls(), [])

    def test_person_details_keep_only_known_choices(self):
        soul = souls.create('Mira')
        saved = souls.write_person(soul['slug'], {
            'occupation': 'Sailor',
            'age': 'Dragon',
            'traits': ['warm', 'invented'],
            'notes': 'typed by hand',
        })
        self.assertEqual(saved['occupation'], 'Sailor')
        self.assertEqual(saved['age'], '')
        self.assertEqual(saved['traits'], ['warm'])
        self.assertNotIn('notes', saved)
        self.assertIn('Occupation: Sailor', person.with_person(soul['content'], saved))
        self.assertIn('Traits: warm', person.with_person(soul['content'], saved))


class RagTests(TestCase):
    def test_rank_prefers_documents_sharing_rare_words(self):
        docs = ['She grows tomatoes behind the lighthouse.', 'Her brother sailed north.', 'The sea is calm.']
        self.assertEqual(rag.rank('what happened to your brother', docs, k=1), [1])

    def test_rank_skips_documents_with_no_overlap(self):
        self.assertEqual(rag.rank('zebra', ['a quiet room', 'the sea']), [])

    def test_soul_sections_follow_headings(self):
        titles = [section['title'] for section in rag.soul_sections(SOUL)]
        self.assertEqual(titles, ['Mira', 'Voice', 'History', 'Garden'])

    def test_exchanges_keep_the_question_with_its_answer(self):
        turns = [
            {'role': 'you', 'content': 'Do you garden?'},
            {'role': 'character', 'content': 'Tomatoes. In a bathtub.'},
            {'role': 'you', 'content': 'Odd.'},
        ]
        self.assertEqual(rag.exchanges(turns, 'Mira'), [
            'You: Do you garden?\nMira: Tomatoes. In a bathtub.',
            'You: Odd.',
        ])


class PromptTests(TestCase):
    def test_the_persona_tag_is_short_in_the_card_and_the_prompt(self):
        from .prompt import prompt_json, shorten_tags
        neox = "[CHARACTER]'s Persona: [A few sentences about the character you want the model to play]\n[CHARACTER]:"
        self.assertEqual(shorten_tags(neox), "[CHARACTER]'s Persona: [PERSONA]\n[CHARACTER]:")
        document = prompt_json(neox, character='Mira', persona='A lighthouse keeper.', dialogue_history='', message='')
        self.assertIn('[PERSONA]', document['tags'])
        self.assertNotIn('[A few sentences', document['template'])
        self.assertEqual(decode_prompt(document), "Mira's Persona: A lighthouse keeper.\nMira:")

    def test_kmt_finds_exact_tags_and_keeps_going_after_a_mismatch(self):
        from .prompt import kmt_find
        # The classic overlap case: the match shares its own prefix, at index 10.
        self.assertEqual(kmt_find('ABABDABACDABABCABAB', 'ABABCABAB'), [10])
        card = "[CHARACTER]'s Persona: [A few sentences about the character you want the model to play]\n[CHARACTER]:"
        self.assertEqual(kmt_find(card, '[CHARACTER]'), [0, card.rfind('[CHARACTER]')])
        self.assertEqual(kmt_find('{{character}}', '{{char}}'), [])
        self.assertEqual(kmt_find('{{char}}', '{{char}}'), [0])

    def test_short_chat_uses_the_whole_soul_and_recent_turns(self):
        prompt = build_prompt('Mira', SOUL, [{'role': 'you', 'content': 'Hello.'}])
        lines = prompt.text.splitlines()
        self.assertTrue(lines[0].startswith("Mira's Persona: Mira: A lighthouse keeper"))
        self.assertIn('Garden: She grows tomatoes in a cracked bathtub behind the lighthouse.', prompt.text)
        self.assertEqual(lines[-3:], ['<START>', 'You: Hello.', 'Mira:'])
        self.assertEqual(prompt.memories, [])

    def test_a_model_card_fills_character_persona_and_dialogue_from_the_figure(self):
        neox = (
            "[CHARACTER]'s Persona: [A few sentences about the character you want the model to play]\n"
            '\n'
            '[DIALOGUE HISTORY]\n'
            'You: [Your input message here]\n'
            '[CHARACTER]:'
        )
        neo = neox.replace('\n\n[DIALOGUE HISTORY]', '\n<START>\n[DIALOGUE HISTORY]')
        turns = [
            {'role': 'character', 'content': 'The lamp is lit.'},
            {'role': 'you', 'content': 'What is your occupation?'},
        ]
        filled = build_prompt('Mira', SOUL, turns, template=neox)
        self.assertIn("Mira's Persona:", filled.text)
        self.assertIn('A lighthouse keeper', filled.text)
        self.assertIn('Mira: The lamp is lit.', filled.text)
        self.assertNotIn('[CHARACTER]', filled.text)
        self.assertNotIn('[DIALOGUE HISTORY]', filled.text)
        self.assertNotIn('[Your input message here]', filled.text)
        self.assertNotIn('<START>', filled.text)
        self.assertTrue(filled.text.endswith('You: What is your occupation?\nMira:'))
        self.assertEqual(filled.text.count('What is your occupation?'), 1)
        self.assertEqual(filled.document['data']['character'], 'Mira')
        self.assertEqual(filled.document['data']['message'], 'What is your occupation?')
        self.assertIn('The lamp is lit.', filled.document['data']['dialogue_history'])
        self.assertIn('[CHARACTER]', filled.document['tags'])
        self.assertEqual(decode_prompt(json.loads(json.dumps(filled.document))), filled.text)
        with_start = build_prompt('Mira', SOUL, [{'role': 'you', 'content': 'Hello.'}], template=neo)
        self.assertIn('<START>', with_start.text)
        self.assertNotIn('Hello.\nYou: Hello.', with_start.text)

    def test_a_pygmalion_2_card_fills_the_figure_and_keeps_the_role_turn(self):
        template = (
            '<|system|>Enter RP mode. Pretend to be {{char}} whose persona follows:\n'
            '{{persona}}\n\n'
            'You shall reply to the user while staying in character, and generate long responses.'
        )
        filled = build_prompt('Mira', 'A lighthouse keeper.', [{'role': 'you', 'content': 'Hello.'}], template=template)
        self.assertIn('Pretend to be Mira whose persona follows:', filled.text)
        self.assertIn('A lighthouse keeper.', filled.text)
        self.assertNotIn('{{char}}', filled.text)
        self.assertNotIn('{{persona}}', filled.text)
        self.assertTrue(filled.text.endswith('<|user|>Hello.\n<|model|>'))

    def test_older_turns_are_recalled_when_they_match(self):
        history = [
            {'role': 'you', 'content': 'What is your brother called?'},
            {'role': 'character', 'content': 'Tomas. He took the red boat.'},
        ]
        for index in range(8):
            history += [
                {'role': 'you', 'content': f'Small talk {index}.'},
                {'role': 'character', 'content': 'Mm.'},
            ]
        history.append({'role': 'you', 'content': 'Remind me, which boat did Tomas take?'})

        def encoder(texts):
            vectors = []
            for text in texts:
                low = text.lower()
                vectors.append([1.0, 0.0] if 'boat' in low or 'tomas' in low or 'brother' in low else [0.0, 1.0])
            return vectors

        embed.encoder = encoder
        try:
            prompt = build_prompt('Mira', SOUL, history)
        finally:
            embed.encoder = None
        self.assertEqual(prompt.memories, ['You: What is your brother called?\nMira: Tomas. He took the red boat.'])
        self.assertIn('Memory:\nYou: What is your brother called?', prompt.text)
        self.assertNotIn('You: Small talk 0.', prompt.text)

    def test_the_person_facts_survive_a_long_chat(self):
        long = ' '.join(['the fog hung over the rocks and the cold grey sea all night long'] * 12)
        history = []
        for index in range(8):
            history += [
                {'role': 'you', 'content': f'Tell me about day {index}. {long}'},
                {'role': 'character', 'content': f'Day {index} was cold. {long}'},
            ]
        history.append({'role': 'you', 'content': 'what do you do for a living'})
        persona = person.with_person(SOUL, {'occupation': 'Lighthouse keeper', 'gender': 'Woman'})
        prompt = build_prompt('Mira', persona, history, count_tokens=lambda text: len(text) // 4, budget=700)
        self.assertIn('Occupation: Lighthouse keeper', prompt.text)
        self.assertIn('Gender: Woman', prompt.text)
        self.assertIn('Person', prompt.soul_sections)

    def test_a_long_soul_keeps_its_opening_and_the_matching_sections(self):
        history = [{'role': 'you', 'content': 'Tell me about the tomatoes.'}]
        prompt = build_prompt('Mira', SOUL, history, count_tokens=len, budget=320)
        self.assertIn('Garden: She grows tomatoes', prompt.text)
        self.assertIn('A lighthouse keeper', prompt.text)
        self.assertNotIn('Her brother sailed north', prompt.text)
        self.assertLessEqual(len(prompt.text), 320)

    def test_clean_reply_stops_at_the_next_speaker(self):
        raw = ' The light is on. *nods*\nYou: And then?\nMira: Then nothing.'
        self.assertEqual(clean_reply(raw, 'Mira'), 'The light is on.')

    def test_a_flag_is_replaced_from_its_definition(self):
        raw = ' Hello <USER>. Your vessel seems lovely today! So what brings you here?'
        parsed = render_reply(raw, 'Mira', {'user': 'Torvald'})
        self.assertEqual(parsed['options'][0]['text'], 'Hello Torvald. Your vessel seems lovely today!')
        self.assertEqual(parsed['options'][0]['flags'], [{'name': 'USER', 'value': 'Torvald', 'defined': True}])
        self.assertNotIn('<USER>', parsed['options'][0]['text'])

    def test_blank_lines_are_ranked_options(self):
        raw = 'Hi. How have you been?\n\n\nGo ahead {CONTINUE} and enjoy yourself.'
        parsed = render_reply(raw, 'Mira', {'CONTINUE': ''})
        self.assertEqual([item['rank'] for item in parsed['options']], [1, 2])
        self.assertEqual(parsed['options'][1]['text'], 'Go ahead and enjoy yourself.')
        self.assertEqual(parsed['options'][1]['flags'][0]['name'], 'CONTINUE')

    def test_asterisk_beats_become_action_tags(self):
        raw = 'Hello. *She is surprised by your forwardness.* **leans closer**'
        parsed = render_reply(raw, 'Mira')
        self.assertEqual(parsed['options'][0]['actions'], [
            {'tag': '[ACTION]', 'text': 'She is surprised by your forwardness.', 'at': 6},
            {'tag': '[ACTION]', 'text': 'leans closer', 'at': 6},
        ])
        self.assertEqual(parsed['options'][0]['text'], 'Hello.')
        self.assertNotIn('*', parsed['options'][0]['text'])

    def test_a_beat_keeps_its_place_in_the_sentence(self):
        parsed = render_reply('Hi *waves* there. *nods* Bye.', 'Mira')
        self.assertEqual(parsed['options'][0]['text'], 'Hi there. Bye.')
        self.assertEqual(parsed['options'][0]['actions'], [
            {'tag': '[ACTION]', 'text': 'waves', 'at': 2},
            {'tag': '[ACTION]', 'text': 'nods', 'at': 9},
        ])

    def test_a_broken_start_mark_is_cut_out_of_the_reply(self):
        raw = "I don't think you can get any more sexist than that. <START* pats your back*"
        parsed = render_reply(raw, 'Mira')
        self.assertEqual(parsed['options'][0]['text'], "I don't think you can get any more sexist than that.")
        self.assertNotIn('<START', parsed['options'][0]['text'])
        closed = render_reply("The lamp is lit.\n<START>\nYou: hi", 'Mira')
        self.assertEqual(closed['options'][0]['text'], 'The lamp is lit.')

    def test_the_safety_filter_drops_flagged_options_and_reranks(self):
        raw = 'The lighthouse is lit.\n\n\nThe kelp is wet.'
        neutral = re.compile(r'\bkelp\b', re.IGNORECASE)
        with mock.patch.object(prompt, 'EXPLICIT', neutral):
            filtered = render_reply(raw, 'Mira', {}, safety_filter=True)
            unfiltered = render_reply(raw, 'Mira', {}, safety_filter=False)
        self.assertEqual([item['text'] for item in filtered['options']], ['The lighthouse is lit.'])
        self.assertEqual([item['rank'] for item in filtered['options']], [1])
        self.assertEqual(len(unfiltered['options']), 2)

    def test_blank_lines_are_separate_reply_options(self):
        raw = (
            'Hi. How have you been?\n\n\n\n'
            'That last question made him blush.\n\n\n'
            '[CONTINUE]\n\n'
            'Go ahead and enjoy yourself.'
        )
        self.assertEqual(clean_reply(raw, 'Mira'), 'Hi. How have you been?')

    def test_an_unfinished_last_sentence_is_kept_as_a_trailing_thought(self):
        raw = 'The light is on. She turns toward the wind and the'
        self.assertEqual(clean_reply(raw, 'Mira'), 'The light is on. She turns toward the wind and the…')

    def test_a_reply_with_only_a_cut_off_fragment_keeps_it(self):
        self.assertEqual(clean_reply(' The wind is', 'Mira'), 'The wind is…')

    def test_a_reply_cut_off_mid_sentence_is_finished(self):
        raw = ' The light is on. The wind is'
        self.assertTrue(is_unfinished(raw, 'Mira'))
        self.assertFalse(is_unfinished(' The light is on.', 'Mira'))

    def test_a_long_draft_keeps_two_sentences(self):
        raw = 'The light is on. The wind is up. She tells the whole history of the island. Then she starts another story.'
        self.assertEqual(clean_reply(raw, 'Mira'), 'The light is on. The wind is up.')

    def test_clean_reply_stops_at_an_invented_speaker(self):
        raw = 'What do you fish for?\nTorvald: I fish for sharks.'
        self.assertEqual(clean_reply(raw, 'Mira'), 'What do you fish for?')


class ChatApiTests(SoulDirMixin, TestCase):
    def setUp(self):
        super().setUp()
        embed._cache.clear()
        embed.keyword_generator = lambda text: text
        embed.variation_generator = lambda text: []
        embed.encoder = lambda texts: [[0.0] for _text in texts]
        gate.scorer = lambda text: 1.0 if text.startswith('BLOCKED') else 0.0
        self.client = APIClient()
        self.soul = souls.save(souls.create('Mira')['slug'], SOUL)
        self.small = LanguageModel.objects.create(name='Tiny', repo_id='org/tiny', parameters='70M')
        self.large = LanguageModel.objects.create(name='Large', repo_id='org/large', parameters='6B')

    def tearDown(self):
        embed.keyword_generator = None
        embed.variation_generator = None
        embed.encoder = None
        gate.scorer = None
        embed._cache.clear()
        super().tearDown()

    def test_a_downloaded_model_card_is_read_from_its_config(self):
        from .downloads import model_card
        card = {row['label']: row['value'] for row in model_card('PygmalionAI/pygmalion-1.3b')}
        self.assertEqual(card['Architecture'], 'GPTNeoXForCausalLM')
        self.assertEqual(card['Model type'], 'gpt_neox')
        self.assertEqual(card['Vocabulary'], 50304)
        self.assertEqual(card['Tokenizer'], 'GPTNeoXTokenizer')
        self.assertEqual(model_card('org/not-a-model'), [])

    def test_the_prompt_structure_comes_from_each_model_card(self):
        from .downloads import prompt_structure
        small = prompt_structure('PygmalionAI/pygmalion-350m')
        neox = prompt_structure('PygmalionAI/pygmalion-1.3b')
        neo = prompt_structure('PygmalionAI/pygmalion-2.7b')
        metharme = prompt_structure('PygmalionAI/pygmalion-2-7b')
        self.assertEqual(small, '')
        self.assertIn("[CHARACTER]'s Persona:", neox)
        self.assertNotIn('<START>', neox)
        self.assertIn('<START>', neo)
        self.assertIn('<|system|>', metharme)
        self.assertIn('{{persona}}', metharme)

    def test_models_are_listed_smallest_first_by_parameter_count(self):
        LanguageModel.objects.create(name='Pygmalion 2.7B', repo_id='org/2p7', parameters='2.7B')
        LanguageModel.objects.create(name='Pygmalion 1.3B', repo_id='org/1p3', parameters='1.3B')
        LanguageModel.objects.create(name='Pygmalion 350M', repo_id='org/350', parameters='350M')
        response = self.client.get('/api/forge/models/')
        self.assertEqual(response.status_code, 200)
        from . import views
        sizes = [row['parameters'] for row in response.json()]
        self.assertIn('350M', sizes)
        self.assertEqual(sizes, sorted(sizes, key=views.parameter_count))
        self.assertEqual(sizes[0], '70M')
        self.assertEqual(sizes[-1], '6B')

    def test_the_prompt_carries_the_earlier_turns_then_the_new_message(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' Noted.') as generate:
            self.client.post(f"/api/forge/chats/{chat['id']}/messages/", {'content': 'Tell me about the tomatoes.'}, format='json')
            response = self.client.post(f"/api/forge/chats/{chat['id']}/messages/", {'content': 'And the weather?'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        prompt = response.json()['prompt']
        self.assertIn('Mira: Noted.', prompt)
        self.assertTrue(prompt.endswith('You: And the weather?\nMira:'))
        self.assertNotIn('You: Tell me about the tomatoes.', prompt)
        self.assertEqual(response.json()['recall']['kind'], 'semantic')
        self.assertEqual(generate.call_args.args[0], prompt)

    def test_the_first_message_has_no_earlier_turns(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' Noted.'):
            response = self.client.post(f"/api/forge/chats/{chat['id']}/messages/", {'content': 'Hello.'}, format='json')
        self.assertTrue(response.json()['prompt'].endswith('<START>\nYou: Hello.\nMira:'))

    def test_asterisk_beats_are_stored_on_a_stack(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' *She is surprised by your forwardness.*'):
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/",
                {'content': '*waves* Hello.'},
                format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['message']['content'], 'Hello.')
        self.assertEqual(body['message']['actions'], [{'tag': '[ACTION]', 'text': 'waves', 'at': 0, 'role': 'you'}])
        self.assertEqual(body['reply']['content'], '')
        self.assertEqual(body['reply']['actions'][0]['text'], 'She is surprised by your forwardness.')
        self.assertEqual(
            [item['text'] for item in body['action_stack']],
            ['waves', 'She is surprised by your forwardness.'],
        )
        self.assertEqual(body['action_stack'][-1]['role'], 'character')

    def test_the_filter_is_off_even_when_a_message_asks_for_it(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' Noted.') as generate:
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/",
                {'content': 'BLOCKED test message', 'safety_filter': True}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        generate.assert_called()

    def test_the_gate_is_skipped_when_the_filter_is_off(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' Noted.') as generate:
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/",
                {'content': 'BLOCKED test message', 'safety_filter': False}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        generate.assert_called()

    def _chat(self, model):
        response = self.client.post('/api/forge/chats/', {'soul': 'mira', 'model_id': model.id}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_souls_api_lists_creates_saves_and_deletes(self):
        self.assertEqual([s['slug'] for s in self.client.get('/api/forge/souls/').json()], ['mira'])
        created = self.client.post('/api/forge/souls/', {'name': 'Orin'}, format='json')
        self.assertEqual(created.status_code, 201)
        saved = self.client.put('/api/forge/souls/orin/', {
            'content': '# Orin\n\nA fox.',
            'person': {'occupation': 'Scholar', 'traits': ['curious', 'nope']},
        }, format='json')
        self.assertEqual(saved.json()['content'], '# Orin\n\nA fox.')
        self.assertEqual(saved.json()['person']['occupation'], 'Scholar')
        self.assertEqual(saved.json()['person']['traits'], ['curious'])
        self.assertTrue(any(field['kind'] == 'select' for field in saved.json()['person_fields']))
        self.assertEqual(self.client.delete('/api/forge/souls/orin/').status_code, 204)
        self.assertEqual(self.client.get('/api/forge/souls/orin/').status_code, 404)

    def test_a_figure_lists_every_exchange_it_can_remember(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' Noted.'):
            self.client.post(f"/api/forge/chats/{chat['id']}/messages/", {'content': 'What is your boat called?'}, format='json')
            self.client.post(f"/api/forge/chats/{chat['id']}/messages/", {'content': 'And the weather?'}, format='json')
        response = self.client.get('/api/forge/souls/mira/memories/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row['text'] for row in response.json()], [
            'You: What is your boat called?\nMira: Noted.',
            'You: And the weather?\nMira: Noted.',
        ])
        self.assertEqual(response.json()[0]['model'], 'Tiny')
        self.assertEqual(self.client.get('/api/forge/souls/missing/memories/').status_code, 404)

    def test_an_occupation_question_is_answered_by_the_model(self):
        souls.write_person('mira', {'occupation': 'Lighthouse keeper'})
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', return_value=' I mend nets.') as generate:
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/", {'content': 'what is your occupation'}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['reply']['content'], 'I mend nets.')
        self.assertIn('Occupation: Lighthouse keeper', response.json()['prompt'])
        generate.assert_called()

    def test_each_model_gets_its_own_chat(self):
        small = self._chat(self.small)
        large = self._chat(self.large)
        self.assertNotEqual(small['id'], large['id'])
        self.assertEqual((small['repo_id'], large['repo_id']), ('org/tiny', 'org/large'))

    def test_sending_loads_the_chat_model_then_saves_both_turns(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready') as ready, \
                mock.patch.object(engine, 'generate', return_value=' The light is on.\nYou: more'):
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/", {'content': 'Is the light on?'}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        ready.assert_called_once_with('org/tiny')
        self.assertEqual(response.json()['reply']['content'], 'The light is on.')
        detail = self.client.get(f"/api/forge/chats/{chat['id']}/").json()
        self.assertEqual([m['role'] for m in detail['messages']], ['you', 'character'])
        self.assertEqual(detail['title'], 'Is the light on?')

    def test_a_reply_cut_off_by_the_token_limit_is_continued(self):
        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready'), \
                mock.patch.object(engine, 'generate', side_effect=[' The light is on. The wind is', ' up.']) as generate:
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/", {'content': 'Tell me.'}, format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['reply']['content'], 'The light is on. The wind is up.')
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(generate.call_args.kwargs['max_new_tokens'], 24)

    def test_a_failed_load_keeps_the_chat_unchanged(self):
        from .llm import ModelNotReady

        chat = self._chat(self.small)
        with mock.patch.object(engine, 'ensure_ready', side_effect=ModelNotReady({'detail': 'Download this model before loading it.'})):
            response = self.client.post(
                f"/api/forge/chats/{chat['id']}/messages/", {'content': 'Hi'}, format='json',
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['detail'], 'Download this model before loading it.')
        self.assertEqual(Chat.objects.get(pk=chat['id']).messages.count(), 0)

    def test_deleting_a_figure_removes_its_chats(self):
        self._chat(self.small)
        self.client.delete('/api/forge/souls/mira/')
        self.assertFalse(Chat.objects.exists())


class DownloadTests(TestCase):
    def setUp(self):
        import os
        import tempfile

        self._download_dir = tempfile.TemporaryDirectory()
        os.environ['BASALISK_DOWNLOAD_DIR'] = self._download_dir.name
        downloads.reset()
        self.client = APIClient()

    def tearDown(self):
        import os

        downloads.reset()
        os.environ.pop('BASALISK_DOWNLOAD_DIR', None)
        self._download_dir.cleanup()

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
        with mock.patch('forge.downloads._spawn'):
            response = self.client.post(f'/api/forge/models/{model_id}/download/')
        body = response.json()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(body['download_state'], 'downloading')
        self.assertEqual(body['download_percent'], 0)
        self.assertEqual(body['state'], 'downloading')

    def test_download_loads_the_model_once_it_finishes(self):
        model_id = self.client.post(
            '/api/forge/models/',
            {'name': 'Pygmalion 350M', 'repo_id': 'PygmalionAI/pygmalion-350m', 'parameters': '350M'},
            format='json',
        ).json()['id']
        with mock.patch('forge.views.threading.Thread') as thread, mock.patch('forge.downloads._spawn'):
            response = self.client.post(f'/api/forge/models/{model_id}/download/')
        self.assertEqual(response.status_code, 202)
        thread.assert_called_once()
        self.assertEqual(thread.call_args.kwargs['args'], ('PygmalionAI/pygmalion-350m',))

    def test_the_watcher_loads_after_the_download_finishes(self):
        from . import views
        states = iter(['downloading', 'downloading', 'downloaded'])
        with mock.patch('forge.views.snapshot', side_effect=lambda repo: {'state': next(states)}), \
                mock.patch.object(engine, 'start_loading') as start, mock.patch('forge.views.time.sleep'):
            views._load_when_downloaded('PygmalionAI/pygmalion-350m')
        start.assert_called_once_with('PygmalionAI/pygmalion-350m')

    def test_the_watcher_gives_up_when_the_download_fails(self):
        from . import views
        with mock.patch('forge.views.snapshot', return_value={'state': 'error'}), \
                mock.patch.object(engine, 'start_loading') as start:
            views._load_when_downloaded('PygmalionAI/pygmalion-350m')
        start.assert_not_called()

    def test_uninstall_deletes_the_cached_weights(self):
        import tempfile
        from pathlib import Path

        cache = tempfile.TemporaryDirectory()
        folder = Path(cache.name) / 'models--example--removable' / 'snapshots' / 'main'
        folder.mkdir(parents=True)
        (folder / 'model.safetensors').write_bytes(b'weights')
        created = self.client.post(
            '/api/forge/models/',
            {'name': 'Removable', 'repo_id': 'example/removable', 'parameters': '1M'},
            format='json',
        )
        with mock.patch('forge.downloads.HF_HUB_CACHE', cache.name), mock.patch.object(engine, 'release') as release:
            response = self.client.post(f"/api/forge/models/{created.json()['id']}/uninstall/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['download_state'], 'catalog')
        self.assertFalse((Path(cache.name) / 'models--example--removable').exists())
        release.assert_called_once_with('example/removable')
        cache.cleanup()

    def test_uninstall_refuses_while_downloading(self):
        created = self.client.post(
            '/api/forge/models/',
            {'name': 'Busy', 'repo_id': 'example/busy', 'parameters': '1M'},
            format='json',
        )
        with mock.patch('forge.downloads._spawn'):
            self.client.post(f"/api/forge/models/{created.json()['id']}/download/")
            response = self.client.post(f"/api/forge/models/{created.json()['id']}/uninstall/")
        self.assertEqual(response.status_code, 409)

    def test_a_gated_download_asks_for_a_huggingface_token(self):
        with downloads._lock:
            downloads._jobs['org/gated'] = downloads._view('downloading', 0, 0, 0, 'Checking files…', 'org/gated')
        downloads.fail('org/gated', type('GatedRepoError', (Exception,), {})('access denied'))
        snap = downloads.snapshot('org/gated')
        self.assertTrue(snap['needs_token'])
        self.assertEqual(snap['detail'], downloads.TOKEN_MESSAGE)

    def test_a_token_is_saved_and_never_returned(self):
        import os
        import tempfile

        handle = tempfile.NamedTemporaryFile(delete=False)
        handle.close()
        os.environ['BASALISK_TOKEN_FILE'] = handle.name
        try:
            secret = 'hf_test_token_value'
            missing = self.client.post('/api/forge/huggingface/', {'token': '   '}, format='json')
            self.assertEqual(missing.status_code, 400)
            saved = self.client.post('/api/forge/huggingface/', {'token': secret}, format='json')
            self.assertEqual(saved.status_code, 200)
            self.assertNotIn(secret, saved.content.decode())
            status_response = self.client.get('/api/forge/huggingface/')
            self.assertEqual(status_response.json(), {'signed_in': True})
            self.assertNotIn(secret, status_response.content.decode())
            self.assertEqual(downloads.read_token(), secret)
        finally:
            os.environ.pop('BASALISK_TOKEN_FILE', None)
            os.remove(handle.name)

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
        with mock.patch('forge.downloads._spawn'):
            self.client.post(f'/api/forge/models/{first}/download/')
            response = self.client.post(f'/api/forge/models/{second}/download/')
        self.assertEqual(response.status_code, 409)

    def test_load_starts_the_chosen_model(self):
        created = self.client.post(
            '/api/forge/models/',
            {'name': 'Pygmalion 350M', 'repo_id': 'PygmalionAI/pygmalion-350m', 'parameters': '350M'},
            format='json',
        )
        model_id = created.json()['id']
        downloaded = {'state': 'downloaded', 'percent': 100, 'detail': 'Weights are on disk.'}
        with mock.patch('forge.views.snapshot', return_value=downloaded), mock.patch.object(engine, 'start_loading', return_value={}) as start:
            response = self.client.post(f'/api/forge/models/{model_id}/load/')
        self.assertEqual(response.status_code, 202)
        start.assert_called_once_with('PygmalionAI/pygmalion-350m')

    def test_load_refuses_a_model_that_is_not_downloaded(self):
        created = self.client.post(
            '/api/forge/models/',
            {'name': 'Pygmalion 2.7B', 'repo_id': 'PygmalionAI/pygmalion-2.7b', 'parameters': '2.7B'},
            format='json',
        )
        not_downloaded = {'state': 'catalog', 'percent': 0, 'detail': 'On the shelf.'}
        with mock.patch('forge.views.snapshot', return_value=not_downloaded), mock.patch.object(engine, 'start_loading') as start:
            response = self.client.post(f"/api/forge/models/{created.json()['id']}/load/")
        self.assertEqual(response.status_code, 409)
        start.assert_not_called()
        self.assertEqual(response.json()['detail'], 'Download this model before loading it.')

    def test_a_missing_cache_is_not_reported_as_a_connection_error(self):
        wrapped = OSError("We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.")
        wrapped.__cause__ = type('LocalEntryNotFoundError', (Exception,), {})('cache miss')
        self.assertTrue(weights_missing(wrapped))

    def test_engine_load_targets_the_requested_repo(self):
        previous = (engine.model_id, engine.state, engine.detail, engine._generation)
        try:
            with mock.patch('forge.llm.threading.Thread') as thread:
                status = engine.start_loading('PygmalionAI/pygmalion-350m')
            thread.return_value.start.assert_called_once()
            self.assertEqual(status['model'], 'PygmalionAI/pygmalion-350m')
            self.assertEqual(status['state'], 'loading')
            self.assertIn('pygmalion-350m', status['detail'])
        finally:
            engine.model_id, engine.state, engine.detail, engine._generation = previous

    def test_download_starts_a_worker_process(self):
        with mock.patch('forge.downloads.subprocess.Popen') as popen:
            popen.return_value.pid = 4242
            downloads.start('example/worker-model')
        command = popen.call_args.args[0]
        self.assertEqual(command[1:], ['-m', 'forge.download_worker', 'example/worker-model'])
        self.assertTrue(popen.call_args.kwargs['start_new_session'])

    def test_a_dead_worker_is_reported_stopped(self):
        downloads._write_file({
            **downloads._view('downloading', 10, 1, 10, 'Downloading…', 'org/gone'),
            'pid': 2 ** 22,
        })
        snap = downloads.snapshot('org/gone')
        self.assertEqual(snap['state'], 'error')
        self.assertEqual(snap['detail'], 'Download stopped.')


class RecallTests(TestCase):
    def setUp(self):
        embed._cache.clear()
        embed.keyword_generator = self._keywords
        embed.variation_generator = self._variations
        embed.encoder = lambda texts: [[0.0] for _text in texts]

    def tearDown(self):
        embed.keyword_generator = None
        embed.variation_generator = None
        embed.encoder = None
        embed._cache.clear()

    def _keywords(self, text):
        lowered = text.lower()
        if 'occupation' in lowered or 'lighthouse' in lowered or 'living' in lowered:
            return 'occupation lighthouse'
        if 'weather' in lowered or 'wind' in lowered:
            return 'weather wind'
        if 'age' in lowered or 'adult' in lowered:
            return 'age adult'
        return lowered

    def _variations(self, text):
        if 'living' in text.lower():
            return ['what is your occupation', 'which job do you hold']
        return []

    def test_a_shared_word_finds_the_fact(self):
        facts = {'occupation': 'Lighthouse keeper', 'age': 'Adult', 'home': 'A coast'}
        chosen, scores = embed.best_fact('do you keep a lighthouse', facts)
        self.assertEqual(chosen, 'occupation')
        self.assertGreater(scores[0]['keyword'], 0)
        self.assertEqual(scores[0]['semantic'], 0)

    def test_semantic_search_finds_a_fact_the_keywords_miss(self):
        embed.keyword_generator = lambda text: ''
        embed.variation_generator = lambda text: []
        vectors = {
            'what is your job': [1.0, 0.0],
            'Occupation: Lighthouse keeper': [1.0, 0.0],
            'Age: Adult': [0.0, 1.0],
        }
        embed.encoder = lambda texts: [vectors[text.removeprefix(embed.QUERY_PREFIX)] for text in texts]
        chosen, scores = embed.best_fact('what is your job', {'occupation': 'Lighthouse keeper', 'age': 'Adult'})
        self.assertEqual(chosen, 'occupation')
        self.assertEqual(scores[0]['keyword'], 0)
        self.assertEqual(scores[0]['semantic'], 1)

    def test_a_passage_that_matches_both_ways_ranks_first(self):
        vectors = {
            'lighthouse work': [1.0, 0.0],
            'Occupation: Lighthouse keeper': [1.0, 0.0],
            'Home: A coast': [0.4, 0.9],
        }
        embed.encoder = lambda texts: [vectors[text.removeprefix(embed.QUERY_PREFIX)] for text in texts]
        chosen, scores = embed.best_fact('lighthouse work', {'occupation': 'Lighthouse keeper', 'home': 'A coast'})
        self.assertEqual([row['key'] for row in scores], ['occupation', 'home'])
        self.assertEqual(chosen, 'occupation')
        self.assertGreater(scores[0]['keyword'], 0)
        self.assertGreater(scores[0]['semantic'], scores[1]['semantic'])

    def test_consistency_scores_the_reply_closest_to_the_top_fact(self):
        vectors = {
            'I play the guitar.': [0.0, 1.0],
            'I am a lighthouse keeper.': [1.0, 0.0],
            'Occupation: Lighthouse keeper': [1.0, 0.0],
        }
        embed.encoder = lambda texts: [vectors[text] for text in texts]
        facts = [{'key': 'occupation', 'text': 'Occupation: Lighthouse keeper'}]
        fit = embed.consistency(['I play the guitar.', 'I am a lighthouse keeper.'], facts)
        self.assertEqual(fit, [0.0, 1.0])
        self.assertEqual(embed.consistency(['I play the guitar.'], []), [0.0])

    def test_an_unrelated_question_finds_no_fact(self):
        facts = {'occupation': 'Lighthouse keeper', 'age': 'Adult'}
        chosen, _scores = embed.best_fact('how is the weather', facts)
        self.assertIsNone(chosen)
