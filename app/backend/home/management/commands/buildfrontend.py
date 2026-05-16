import shutil
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Build the Vite React app (app/frontend) for Django to serve.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--install',
            action='store_true',
            help='Run npm install before building.',
        )

    def handle(self, *args, **options):
        frontend_root = settings.FRONTEND_ROOT
        if not frontend_root.is_dir():
            raise CommandError(f'Frontend directory not found: {frontend_root}')

        npm = shutil.which('npm')
        if not npm:
            raise CommandError('npm is not on PATH. Install Node.js to build the frontend.')

        if options['install']:
            self.stdout.write('Running npm install…')
            subprocess.run([npm, 'install'], cwd=frontend_root, check=True)

        self.stdout.write('Running npm run build…')
        subprocess.run([npm, 'run', 'build'], cwd=frontend_root, check=True)

        build_dir = settings.FRONTEND_BUILD_DIR
        if not (build_dir / 'index.html').is_file():
            raise CommandError(f'Build finished but {build_dir / "index.html"} is missing.')

        self.stdout.write(self.style.SUCCESS(f'Frontend built at {build_dir}'))
