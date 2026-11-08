from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .downloads import DownloadBusy, start as start_download
from .llm import ModelNotReady, engine
from .models import LanguageModel, Persona
from .prompt import build_prompt, clean_reply
from .serializers import ConversationSerializer, LanguageModelSerializer, PersonaSerializer


def forge_page(request):
    return render(request, 'forge/index.html')


class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer


class LanguageModelViewSet(viewsets.ModelViewSet):
    queryset = LanguageModel.objects.all()
    serializer_class = LanguageModelSerializer

    def _is_live(self, model):
        return bool(model.repo_id) and model.repo_id == engine.status()['model']

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
        if self._is_live(model):
            return Response(engine.start_loading(), status=status.HTTP_202_ACCEPTED)
        return Response(LanguageModelSerializer(model).data)


def _conversation(request):
    serializer = ConversationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class MoldView(APIView):
    """Show the exact prompt Pygmalion will receive for an unsaved draft."""

    def post(self, request):
        data = _conversation(request)
        budget = engine.context_tokens - data['sampling']['max_new_tokens']
        prompt = build_prompt(data['persona'], data['history'], engine.count_tokens, budget)
        return Response({'prompt': prompt, 'tokens': engine.count_tokens(prompt)})


class SpeakView(APIView):
    def post(self, request):
        data = _conversation(request)
        history = data['history']
        if not history or history[-1]['role'] != 'you':
            return Response({'detail': 'Say something first.'}, status=status.HTTP_400_BAD_REQUEST)

        sampling = data['sampling']
        budget = engine.context_tokens - sampling['max_new_tokens']
        prompt = build_prompt(data['persona'], history, engine.count_tokens, budget)
        try:
            raw = engine.generate(prompt, **sampling)
        except ModelNotReady as exc:
            return Response({'detail': str(exc), 'model': exc.status}, status=status.HTTP_409_CONFLICT)

        reply = clean_reply(raw, data['persona']['name'])
        return Response({'reply': reply, 'raw': raw, 'prompt': prompt})


class ModelView(APIView):
    def get(self, request):
        return Response(engine.status())

    def post(self, request):
        return Response(engine.start_loading(), status=status.HTTP_202_ACCEPTED)
