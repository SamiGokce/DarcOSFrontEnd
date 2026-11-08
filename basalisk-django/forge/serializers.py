from rest_framework import serializers

from . import downloads
from .llm import engine
from .models import TEMPERAMENT_AXES, LanguageModel, Persona, default_temperament


class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = [
            'id', 'name', 'epithet', 'traits', 'temperament', 'personality', 'appearance',
            'scenario', 'speaking_style', 'greeting', 'example_dialogue', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Give the figure a name.')
        return value

    def validate_traits(self, value):
        if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
            raise serializers.ValidationError('Traits must be a list of words.')
        traits = [t.strip()[:40] for t in value if t.strip()]
        if len(traits) > 24:
            raise serializers.ValidationError('Keep it to 24 traits or fewer.')
        return traits

    def validate_temperament(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Temperament must be an object.')
        cleaned = default_temperament()
        for axis in TEMPERAMENT_AXES:
            if axis in value:
                try:
                    cleaned[axis] = max(0, min(100, int(value[axis])))
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError(f'{axis} must be a number from 0 to 100.') from exc
        return cleaned


class LanguageModelSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    download_state = serializers.SerializerMethodField()
    download_percent = serializers.SerializerMethodField()
    download_detail = serializers.SerializerMethodField()

    class Meta:
        model = LanguageModel
        fields = [
            'id', 'name', 'repo_id', 'parameters', 'context_tokens', 'notes',
            'state', 'detail', 'device', 'download_state', 'download_percent', 'download_detail',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'state', 'detail', 'device', 'download_state', 'download_percent', 'download_detail']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Give the model a name.')
        return value

    def _live(self, obj):
        status = engine.status()
        if obj.repo_id and obj.repo_id == status['model']:
            return status
        return None

    def _download(self, obj):
        cache = getattr(self, '_download_cache', None)
        if cache is None:
            cache = {}
            self._download_cache = cache
        if obj.pk not in cache:
            cache[obj.pk] = downloads.snapshot(obj.repo_id)
        return cache[obj.pk]

    def get_download_state(self, obj):
        return self._download(obj)['state']

    def get_download_percent(self, obj):
        return self._download(obj)['percent']

    def get_download_detail(self, obj):
        return self._download(obj)['detail']

    def get_state(self, obj):
        download = self._download(obj)
        if download['state'] == 'downloading':
            return 'downloading'
        live = self._live(obj)
        if live and live['state'] != 'idle':
            return live['state']
        if download['state'] == 'downloaded':
            return 'downloaded'
        if download['state'] == 'error':
            return 'error'
        return 'catalog'

    def get_detail(self, obj):
        download = self._download(obj)
        if download['state'] == 'downloading':
            return download['detail']
        live = self._live(obj)
        if live and live['state'] != 'idle':
            return live['detail']
        return download['detail']

    def get_device(self, obj):
        live = self._live(obj)
        return live['device'] if live else None


class TurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['you', 'character'])
    content = serializers.CharField(max_length=4000, trim_whitespace=True)


class SamplingSerializer(serializers.Serializer):
    max_new_tokens = serializers.IntegerField(min_value=1, max_value=512, default=120)
    temperature = serializers.FloatField(min_value=0, max_value=2, default=0.8)
    top_p = serializers.FloatField(min_value=0.05, max_value=1, default=0.9)
    repetition_penalty = serializers.FloatField(min_value=1, max_value=2, default=1.1)


class ConversationSerializer(serializers.Serializer):
    persona = PersonaSerializer()
    history = TurnSerializer(many=True, default=list)
    sampling = SamplingSerializer(default=dict)

    def validate_history(self, value):
        if len(value) > 200:
            raise serializers.ValidationError('Conversation is too long; clear it to continue.')
        return value

    def validate(self, attrs):
        # A default skips nested validation, so an omitted `sampling` would arrive without its field defaults.
        if not attrs.get('sampling'):
            sampling = SamplingSerializer(data={})
            sampling.is_valid(raise_exception=True)
            attrs['sampling'] = sampling.validated_data
        return attrs
