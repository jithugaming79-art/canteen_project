from django.test import TestCase, Client
from django.urls import reverse

class OfflinePageTest(TestCase):
    def test_offline_page_status_code(self):
        client = Client()
        response = client.get(reverse('offline'))
        self.assertEqual(response.status_code, 200)

    def test_offline_page_template(self):
        client = Client()
        response = client.get(reverse('offline'))
        self.assertTemplateUsed(response, 'offline.html')
