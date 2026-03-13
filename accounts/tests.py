from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.urls import reverse
from menu.models import Category, MenuItem
from orders.models import Order, OrderItem
from decimal import Decimal
from django.core.cache import cache

class AdminDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Admin User
        self.admin_user = User.objects.create_user(username='admin', password='password')
        self.admin_user.profile.role = 'admin'
        self.admin_user.profile.save()
        
        # Create Student User
        self.student_user = User.objects.create_user(username='student', password='password')
        
        # Setup SocialApp for templates
        site = Site.objects.get_current()
        google_app, _ = SocialApp.objects.get_or_create(provider='google', name='Google')
        google_app.sites.add(site)
        
        # Create Menu Item
        self.category = Category.objects.create(name="Snacks")
        self.item = MenuItem.objects.create(
            category=self.category, 
            name="Burger", 
            price=100,
            is_available=True
        )
        
        # Create Order
        self.order = Order.objects.create(
            user=self.student_user,
            total_amount=100,
            status='pending'
        )
        OrderItem.objects.create(
            order=self.order,
            menu_item=self.item,
            item_name="Burger",
            price=100,
            quantity=1
        )

    def test_admin_access(self):
        self.client.force_login(self.admin_user)
        # Using custom_admin_overview since admin_dashboard is a RedirectView now
        response = self.client.get(reverse('custom_admin_overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Orders")
    
    def test_student_access_denied(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('custom_admin_overview'))
        self.assertEqual(response.status_code, 302) # Redirects to home
    
    def test_update_order_status(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('custom_admin_orders'), {
            'order_id': self.order.id,
            'status': 'confirmed'
        })
        self.assertEqual(response.status_code, 302) # Redirects back to dashboard
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')
        
    def test_toggle_menu_availability(self):
        self.client.force_login(self.admin_user)
        self.assertTrue(self.item.is_available)
        
        response = self.client.post(reverse('custom_admin_menu'), {
            'toggle_item': 'true',
            'item_id': self.item.id
        })
        
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_available)


class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='oldpassword123')
        # Setup SocialApp for templates
        site = Site.objects.get_current()
        google_app, _ = SocialApp.objects.get_or_create(provider='google', name='Google')
        google_app.sites.add(site)
        # Clear cache before tests for rate limiting
        cache.clear()

    def test_honeypot_rejects_bots(self):
        response = self.client.post(reverse('register'), {
            'username': 'botuser',
            'email': 'bot@test.com',
            'password1': 'StrongP@ssw0rd123!',
            'password2': 'StrongP@ssw0rd123!',
            'full_name': 'Bot',
            'phone': '9876543210',
            'website': 'http://spam.com', # Honeypot filled
            'form_load_time': '0'
        })
        self.assertEqual(response.status_code, 200) # Returns to form
        self.assertContains(response, 'Registration failed')
        self.assertFalse(User.objects.filter(username='botuser').exists())

    def test_username_sanitization(self):
        response = self.client.post(reverse('register'), {
            'username': '<script>alert(1)</script>',
            'email': 'test@test.com',
            'password1': 'StrongP@ssw0rd123!',
            'password2': 'StrongP@ssw0rd123!',
            'full_name': 'Test',
            'phone': '9876543210',
            'form_load_time': '0'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username can only contain')
        
    def test_registration_rate_limit(self):
        # Submit 6 registrations
        for i in range(6):
            response = self.client.post(reverse('register'), {
                'username': f'user{i}',
                'email': f'user{i}@test.com',
                'password1': 'StrongP@ssw0rd123!',
                'password2': 'StrongP@ssw0rd123!',
                'full_name': 'Test',
                'phone': '9876543210',
                'form_load_time': '0'
            })
            
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many accounts created')

    def test_generic_login_error(self):
        # Non-existent user
        response1 = self.client.post(reverse('login'), {
            'username': 'doesnotexist',
            'password': 'password123'
        })
        # Existing user, wrong password
        response2 = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        self.assertContains(response1, 'Invalid credentials')
        self.assertContains(response2, 'Invalid credentials')

    def test_password_change_requires_old_password(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('change_password'), {
            'old_password': 'wrongoldpassword',
            'new_password1': 'NewPass123!',
            'new_password2': 'NewPass123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your old password was entered incorrectly')
        
        # Verify password didn't change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpassword123'))
