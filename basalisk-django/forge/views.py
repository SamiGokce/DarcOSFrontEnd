from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import souls
from .downloads import DownloadBusy, start as start_download
from .llm import ModelNotReady, engine
from .models import Chat, LanguageModel, Message
from .prompt import build_prompt, clean_reply
from .serializers import (
    ChatDetailSerializer,
    ChatSerializer,
    LanguageModelSerializer,
    MessageSerializer,
    NewSoulSerializer,
    SendSerializer,
    SoulSerializer,
)


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
        return Response(LanguageModelSerializer(model).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def load(self, request, pk=None):
        model = self.get_object()
        if not model.repo_id:
            return Response({'detail': 'This model has no repository.'}, status=status.HTTP_400_BAD_REQUEST)
        engine.start_loading(model.repo_id)
        return Response(LanguageModelSerializer(model).data, status=status.HTTP_202_ACCEPTED)


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
        return Response(souls.save(slug, body.validated_data['content']))

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
        except ModelNotReady as exc:
            mine.delete()
            return Response({'detail': str(exc), 'model': exc.status}, status=status.HTTP_409_CONFLICT)

        reply = Message.objects.create(chat=chat, role='character', content=clean_reply(raw, soul['name']) or '…')
        if not chat.title:
            chat.title = mine.content[:80]
        chat.save()
        return Response({
            'message': MessageSerializer(mine).data,
            'reply': MessageSerializer(reply).data,
            'prompt': prompt.text,
            'memories': prompt.memories,
            'soul_sections': prompt.soul_sections,
        })


class ModelView(APIView):
    def get(self, request):
        return Response(engine.status())

    def post(self, request):
        return Response(engine.start_loading(), status=status.HTTP_202_ACCEPTED)
