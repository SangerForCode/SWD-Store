from django import forms
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from .forms import ItemForm
from .middleware import BlockUnauthorizedOriginsMiddleware
from .models import Category


class ItemFormSchemaTests(SimpleTestCase):
    def test_category_choices_are_backed_by_a_lazy_model_field(self):
        field = ItemForm.base_fields["category"]
        self.assertIsInstance(field, forms.ModelChoiceField)
        self.assertIs(field.queryset.model, Category)


class LocalOriginMiddlewareTests(SimpleTestCase):
    @override_settings(DEBUG=True)
    def test_debug_loopback_allows_local_development_requests(self):
        request = RequestFactory().get(
            "/",
            HTTP_HOST="127.0.0.1:8000",
            HTTP_USER_AGENT="curl/8.0",
        )
        middleware = BlockUnauthorizedOriginsMiddleware(lambda _request: HttpResponse("ok"))

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
