from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse


def api_health(request):
    return JsonResponse({'status': 'ok', 'service': 'Basalisk'})


def _build_dir() -> Path:
    return Path(settings.FRONTEND_BUILD_DIR).resolve()


def serve_frontend(request, path=''):
    """Serve the Vite production build (static assets + SPA fallback)."""
    build_dir = _build_dir()
    index_path = build_dir / 'index.html'

    if not index_path.is_file():
        return HttpResponse(
            (
                '<h1>Basalisk frontend not built</h1>'
                f'<p>From <code>{settings.FRONTEND_ROOT}</code>, run:</p>'
                '<pre>npm install\nnpm run build</pre>'
            ),
            status=503,
            content_type='text/html',
        )

    if path:
        asset_path = (build_dir / path).resolve()
        try:
            asset_path.relative_to(build_dir)
        except ValueError as exc:
            raise Http404('Invalid path') from exc

        if asset_path.is_file():
            return FileResponse(asset_path.open('rb'))

    return FileResponse(index_path.open('rb'), content_type='text/html')
