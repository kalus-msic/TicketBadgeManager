from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates default user TBM with password TBM'

    def handle(self, *args, **options):
        username = 'TBM'
        password = 'TBM'
        email = 'tbm@localhost'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists'))
        else:
            User.objects.create_user(
                username=username,
                password=password,
                email=email,
                is_staff=True,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}" with password "{password}"'))