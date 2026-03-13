from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Category, MenuItem
from decimal import Decimal

class MenuModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Beverages", description="Soft drinks")
        
    def test_create_menu_item(self):
        item = MenuItem.objects.create(
            category=self.category,
            name="Cola",
            price=Decimal('50.00'),
            description="Chilled cola"
        )
        self.assertEqual(item.name, "Cola")
        self.assertEqual(item.price, Decimal('50.00'))
        self.assertEqual(item.category.name, "Beverages")
        
    def test_str_representation(self):
        item = MenuItem.objects.create(
            category=self.category,
            name="Coffee",
            price=Decimal('20.00')
        )
        self.assertEqual(str(item), "Coffee - ₹20.00")

class MenuViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Snacks")
        MenuItem.objects.create(category=self.category, name="Burger", price=100)

    def test_menu_page_status(self):
        response = self.client.get(reverse('menu'))
        self.assertEqual(response.status_code, 200)
        
    def test_menu_content(self):
        response = self.client.get(reverse('menu'))
        self.assertContains(response, "Burger")
        self.assertContains(response, "Snacks")
