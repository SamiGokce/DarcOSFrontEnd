from django.db import migrations, models


def seed_pygmalion(apps, schema_editor):
    LanguageModel = apps.get_model('forge', 'LanguageModel')
    LanguageModel.objects.get_or_create(
        repo_id='PygmalionAI/pygmalion-1.3b',
        defaults={
            'name': 'Pygmalion 1.3B',
            'parameters': '1.3B',
            'context_tokens': 2048,
            'notes': 'The chat model. Weights are the GPT-NeoX checkpoint from Hugging Face.',
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('forge', '0002_seed_galatea'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanguageModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('repo_id', models.CharField(blank=True, max_length=200)),
                ('parameters', models.CharField(blank=True, max_length=40)),
                ('context_tokens', models.PositiveIntegerField(default=2048)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.RunPython(seed_pygmalion, migrations.RunPython.noop),
    ]
