from django.db import models

TEMPERAMENT_AXES = {
    'warmth': ('reserved', 'warm'),
    'playfulness': ('serious', 'playful'),
    'curiosity': ('content', 'curious'),
    'boldness': ('gentle', 'bold'),
}


def default_temperament():
    return {axis: 50 for axis in TEMPERAMENT_AXES}


class LanguageModel(models.Model):
    """A model on the shelf. Download and load through Hugging Face come later, except the built-in Pygmalion."""

    name = models.CharField(max_length=80)
    repo_id = models.CharField(max_length=200, blank=True)
    parameters = models.CharField(max_length=40, blank=True)
    context_tokens = models.PositiveIntegerField(default=2048)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Persona(models.Model):
    name = models.CharField(max_length=80)
    epithet = models.CharField(max_length=160, blank=True)
    traits = models.JSONField(default=list, blank=True)
    temperament = models.JSONField(default=default_temperament, blank=True)
    personality = models.TextField(blank=True)
    appearance = models.TextField(blank=True)
    scenario = models.TextField(blank=True)
    speaking_style = models.TextField(blank=True)
    greeting = models.TextField(blank=True)
    example_dialogue = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name
