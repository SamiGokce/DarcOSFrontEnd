import threading
import time

from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import souls
from .downloads import DownloadBusy, remove as remove_download, save_token, signed_in, snapshot, start as start_download
from .llm import ModelNotReady, engine
from .models import Chat, LanguageModel, Message
from .prompt import build_prompt, is_unfinished, render_reply

FINISH_TOKENS = 24  # extra tokens allowed to complete a sentence cut off by max_new_tokens
from .serializers import (
    ChatDetailSerializer,
    ChatSerializer,
    LanguageModelSerializer,
    MessageSerializer,
    NewSoulSerializer,
    SendSerializer,
    SoulSerializer,
)


def _load_when_downloaded(repo_id, poll_seconds=1.0, timeout_seconds=12 * 60 * 60):
    """Load the model into the engine once its download finishes, so Download alone is enough."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = snapshot(repo_id)['state']
        if state == 'downloaded':
            engine.start_loading(repo_id)
            return
        if state != 'downloading':
            return
        time.sleep(poll_seconds)


class LanguageModelViewSet(viewsets.ModelViewSet):
    queryset = LanguageModel.objects.all()
    serializer_class = LanguageModelSerializer

    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        model = self.get_object()
        if not model.repo_id:
            return Response({'detail': 'This model has no repository.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            start_download(model.repo_id)
        except DownloadBusy as exc:
            return Response({'detail': f'Already downloading {exc.repo_id}.'}, status=status.HTTP_409_CONFLICT)
        threading.Thread(target=_load_when_downloaded, args=(model.repo_id,), name='load-after-download', daemon=True).start()
        return Response(LanguageModelSerializer(model).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def load(self, request, pk=None):
        model = self.get_object()
        if not model.repo_id:
            return Response({'detail': 'This model has no repository.'}, status=status.HTTP_400_BAD_REQUEST)
        if snapshot(model.repo_id)['state'] != 'downloaded':
            return Response({'detail': 'Download this model before loading it.'}, status=status.HTTP_409_CONFLICT)
        engine.start_loading(model.repo_id)
        return Response(LanguageModelSerializer(model).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def uninstall(self, request, pk=None):
        model = self.get_object()
        if not model.repo_id:
            return Response({'detail': 'This model has no repository.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            remove_download(model.repo_id)
        except DownloadBusy as exc:
            return Response({'detail': f'{exc.repo_id} is still downloading.'}, status=status.HTTP_409_CONFLICT)
        engine.release(model.repo_id)
        return Response(LanguageModelSerializer(model).data)


class HuggingFaceView(APIView):
    """Stores a Hugging Face access token locally. The token itself is never returned."""

    def get(self, request):
        return Response({'signed_in': signed_in()})

    def post(self, request):
        token = str(request.data.get('token') or '').strip()
        if not token:
            return Response({'detail': 'Paste a Hugging Face access token.'}, status=status.HTTP_400_BAD_REQUEST)
        save_token(token)
        return Response({'signed_in': True})


class SoulListView(APIView):
    def get(self, request):
        return Response(souls.list_souls())

    def post(self, request):
        body = NewSoulSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            soul = souls.create(body.validated_data['name'])
        except souls.SoulError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(soul, status=status.HTTP_201_CREATED)


class SoulDetailView(APIView):
    def _soul(self, slug):
        try:
            return souls.get(slug)
        except souls.SoulNotFound:
            return None

    def get(self, request, slug):
        soul = self._soul(slug)
        if soul is None:
            return Response({'detail': 'No figure with that name.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(soul)

    def put(self, request, slug):
        if self._soul(slug) is None:
            return Response({'detail': 'No figure with that name.'}, status=status.HTTP_404_NOT_FOUND)
        body = SoulSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        saved = souls.save(slug, body.validated_data['content'])
        if 'flags' in body.validated_data:
            souls.write_flags(slug, body.validated_data['flags'])
            saved = souls.get(slug)
        return Response(saved)

    def delete(self, request, slug):
        if self._soul(slug) is None:
            return Response({'detail': 'No figure with that name.'}, status=status.HTTP_404_NOT_FOUND)
        souls.delete(slug)
        Chat.objects.filter(soul=slug).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Chat.objects.all()

    def get_serializer_class(self):
        return ChatDetailSerializer if self.action == 'retrieve' else ChatSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        soul = self.request.query_params.get('soul')
        return queryset.filter(soul=soul) if soul else queryset

    @action(detail=True, methods=['post'])
    def messages(self, request, pk=None):
        chat = get_object_or_404(Chat, pk=pk)
        body = SendSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            soul = souls.get(chat.soul)
        except souls.SoulNotFound:
            return Response({'detail': 'This chat\'s figure was deleted.'}, status=status.HTTP_410_GONE)

        try:
            engine.ensure_ready(chat.repo_id)
        except ModelNotReady as exc:
            return Response({'detail': str(exc), 'model': exc.status}, status=status.HTTP_409_CONFLICT)

        sampling = body.validated_data['sampling']
        mine = Message.objects.create(chat=chat, role='you', content=body.validated_data['content'].strip())
        history = [{'role': m.role, 'content': m.content} for m in chat.messages.all()]
        budget = engine.context_tokens - sampling['max_new_tokens']
        prompt = build_prompt(soul['name'], soul['content'], history, engine.count_tokens, budget)
        try:
            raw = engine.generate(prompt.text, **sampling)
            if is_unfinished(raw, soul['name']):
                # Cut off by max_new_tokens: let the model finish the sentence it was on.
                raw += engine.generate(prompt.text + raw, **{**sampling, 'max_new_tokens': FINISH_TOKENS})
        except ModelNotReady as exc:
            mine.delete()
            return Response({'detail': str(exc), 'model': exc.status}, status=status.HTTP_409_CONFLICT)

        parsed = render_reply(raw, soul['name'], soul.get('flags') or {})
        reply = Message.objects.create(
            chat=chat, role='character', content=(parsed['options'][0]['text'] if parsed['options'] else '…'),
        )
        if not chat.title:
            chat.title = mine.content[:80]
        chat.save()
        return Response({
            'message': MessageSerializer(mine).data,
            'reply': MessageSerializer(reply).data,
            'prompt': prompt.text,
            'memories': prompt.memories,
            'soul_sections': prompt.soul_sections,
            'options': parsed['options'],
        })


class ModelView(APIView):
    def get(self, request):
        return Response(engine.status())

    def post(self, request):
        return Response(engine.start_loading(), status=status.HTTP_202_ACCEPTED)
