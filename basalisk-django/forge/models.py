from django.db import models


def default_temperament():
    # Migration 0001 imports this for the removed Persona model's field default.
    return {'warmth': 50, 'playfulness': 50, 'curiosity': 50, 'boldness': 50}


class LanguageModel(models.Model):
    """A model on the shelf, downloaded and loaded through Hugging Face."""

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


class Chat(models.Model):
    """One conversation between a soul.md and one model. A new model means a new chat."""

    soul = models.CharField(max_length=63)
    repo_id = models.CharField(max_length=200)
    model_name = models.CharField(max_length=80)
    title = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'{self.soul} on {self.model_name}'


class Message(models.Model):
    ROLES = [('you', 'You'), ('character', 'Character')]

    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField()
    actions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
