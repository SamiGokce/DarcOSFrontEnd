from rest_framework import serializers

from . import downloads
from .llm import engine
from .models import Chat, LanguageModel, Message
from .prompt import shorten_tags


class LanguageModelSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    download_state = serializers.SerializerMethodField()
    download_percent = serializers.SerializerMethodField()
    download_detail = serializers.SerializerMethodField()
    download_needs_token = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    prompt = serializers.SerializerMethodField()

    class Meta:
        model = LanguageModel
        fields = [
            'id', 'name', 'repo_id', 'parameters', 'context_tokens', 'notes',
            'state', 'detail', 'device', 'download_state', 'download_percent', 'download_detail', 'download_needs_token',
            'metadata', 'prompt',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'state', 'detail', 'device', 'download_state', 'download_percent', 'download_detail', 'download_needs_token', 'metadata', 'prompt']

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

    def get_download_needs_token(self, obj):
        return bool(self._download(obj).get('needs_token'))

    def get_metadata(self, obj):
        return downloads.model_card(obj.repo_id)

    def get_prompt(self, obj):
        return shorten_tags(downloads.prompt_structure(obj.repo_id))

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


class SoulSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=True, trim_whitespace=False, max_length=200_000)
    flags = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False)
    person = serializers.JSONField(required=False)


class NewSoulSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'actions', 'created_at']


class ChatSerializer(serializers.ModelSerializer):
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=LanguageModel.objects.all(), write_only=True, source='model',
    )
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            'id', 'soul', 'model_id', 'repo_id', 'model_name', 'title',
            'message_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'repo_id', 'model_name', 'title', 'message_count', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()

    def validate_soul(self, value):
        from . import souls

        try:
            souls.get(value)
        except souls.SoulNotFound as exc:
            raise serializers.ValidationError('No figure with that name.') from exc
        return value

    def validate(self, attrs):
        model = attrs.get('model')
        if model is not None and not model.repo_id:
            raise serializers.ValidationError({'model_id': 'This model has no repository.'})
        return attrs

    def create(self, validated_data):
        model = validated_data.pop('model')
        return Chat.objects.create(repo_id=model.repo_id, model_name=model.name, **validated_data)


class ChatDetailSerializer(ChatSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ChatSerializer.Meta):
        fields = ChatSerializer.Meta.fields + ['messages']


class SamplingSerializer(serializers.Serializer):
    max_new_tokens = serializers.IntegerField(min_value=1, max_value=512, default=48)
    temperature = serializers.FloatField(min_value=0, max_value=2, default=0.5)
    top_p = serializers.FloatField(min_value=0.05, max_value=1, default=0.9)
    repetition_penalty = serializers.FloatField(min_value=1, max_value=2, default=1.0)


class SendSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000)
    sampling = SamplingSerializer(default=dict)
    safety_filter = serializers.BooleanField(default=False)

    def validate(self, attrs):
        # A default skips nested validation, so an omitted `sampling` would arrive without its field defaults.
        if not attrs.get('sampling'):
            sampling = SamplingSerializer(data={})
            sampling.is_valid(raise_exception=True)
            attrs['sampling'] = sampling.validated_data
        return attrs
