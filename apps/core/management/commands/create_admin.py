import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create initial admin user from environment variables (idempotent)'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv('ADMIN_EMAIL', '')
        password = os.getenv('ADMIN_PASSWORD', '')

        if not email or not password:
            self.stdout.write('ADMIN_EMAIL or ADMIN_PASSWORD not set — skipping.')
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f'Admin {email} already exists — skipping.')
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Admin {email} created.'))
