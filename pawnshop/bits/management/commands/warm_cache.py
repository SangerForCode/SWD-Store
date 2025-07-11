from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from bits.views import api_items
from bits.models import Person

class Command(BaseCommand):
    help = 'Warm up frequently accessed cache keys'

    def handle(self, *args, **options):
        factory = RequestFactory()

        test_person = Person.objects.first()
        if not test_person:
            self.stdout.write(self.style.WARNING('No users found. Create a user first.'))
            return
        common_requests = [
            {'c': 'ALL', 's': '0', 'p': '1'},
            {'c': 'ALL', 's': '1', 'p': '1'},
            {'c': 'ALL', 's': '2', 'p': '1'},
        ]

        for params in common_requests:
            try:
                request = factory.get('/api/items/', params)

                middleware = SessionMiddleware(lambda req: None)
                middleware.process_request(request)
                request.session.save()

                request.session['email'] = test_person.email

                response = api_items(request)

                self.stdout.write(
                    self.style.SUCCESS(f"Warmed cache for {params}")
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to warm cache for {params}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS('Cache warming completed!')
        )