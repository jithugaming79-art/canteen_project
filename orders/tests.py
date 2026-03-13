from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from menu.models import Category, MenuItem
from orders.models import Order, OrderItem
from decimal import Decimal


class CartTestCase(TestCase):
    """Tests for cart functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Snacks')
        self.item = MenuItem.objects.create(
            category=self.category,
            name='Test Burger',
            price=Decimal('99.00'),
            is_available=True
        )
    
    def test_add_to_cart(self):
        """Test adding item to cart"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('add_to_cart', args=[self.item.id]),
            {'quantity': 2, 'next': 'view_cart'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        session = self.client.session
        self.assertIn(str(self.item.id), session.get('cart', {}))
        self.assertEqual(session['cart'][str(self.item.id)]['quantity'], 2)
    
    def test_view_cart(self):
        """Test viewing cart"""
        self.client.login(username='testuser', password='testpass123')
        # Add item first
        session = self.client.session
        session['cart'] = {str(self.item.id): {'quantity': 1}}
        session.save()
        
        response = self.client.get(reverse('view_cart'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Burger')
    
    def test_remove_from_cart(self):
        """Test removing item from cart"""
        self.client.login(username='testuser', password='testpass123')
        # Add item first
        session = self.client.session
        session['cart'] = {str(self.item.id): {'quantity': 1}}
        session.save()
        
        response = self.client.post(reverse('remove_from_cart', args=[self.item.id]))
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertNotIn(str(self.item.id), session.get('cart', {}))
    
    def test_clear_cart(self):
        """Test clearing entire cart"""
        self.client.login(username='testuser', password='testpass123')
        session = self.client.session
        session['cart'] = {str(self.item.id): {'quantity': 2}}
        session.save()
        
        response = self.client.post(reverse('clear_cart'))
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session.get('cart', {}), {})


class OrderTestCase(TestCase):
    """Tests for order functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='orderuser',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Meals')
        self.item = MenuItem.objects.create(
            category=self.category,
            name='Test Pizza',
            price=Decimal('199.00'),
            is_available=True
        )
    
    def test_checkout_empty_cart(self):
        """Test checkout with empty cart redirects to menu"""
        self.client.login(username='orderuser', password='testpass123')
        response = self.client.get(reverse('checkout'), follow=False)
        self.assertEqual(response.status_code, 302)  # Redirects somewhere
    
    def test_checkout_with_items(self):
        """Test checkout page with items in cart"""
        self.client.login(username='orderuser', password='testpass123')
        session = self.client.session
        session['cart'] = {str(self.item.id): {'quantity': 1}}
        session.save()
        
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Pizza')
    
    def test_place_order(self):
        """Test placing an order"""
        self.client.login(username='orderuser', password='testpass123')
        session = self.client.session
        session['cart'] = {str(self.item.id): {'quantity': 2}}
        session.save()
        
        response = self.client.post(reverse('place_order'), {
            'payment_method': 'cash',
            'special_instructions': 'Extra cheese please'
        })
        
        # Should redirect to payment page
        self.assertEqual(response.status_code, 302)
        
        # Check order was created
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_amount, Decimal('398.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.special_instructions, 'Extra cheese please')
    
    def test_order_history(self):
        """Test order history page"""
        self.client.login(username='orderuser', password='testpass123')
        # Create a test order
        Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00'),
            status='pending'
        )
        
        response = self.client.get(reverse('order_history'))
        self.assertEqual(response.status_code, 200)
    
    def test_cancel_pending_order(self):
        """Test cancelling a pending order"""
        self.client.login(username='orderuser', password='testpass123')
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00'),
            status='pending'
        )
        
        response = self.client.post(reverse('cancel_order', args=[order.id]))
        self.assertEqual(response.status_code, 302)
        
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
    
    def test_cannot_cancel_preparing_order(self):
        """Test that preparing orders cannot be cancelled"""
        self.client.login(username='orderuser', password='testpass123')
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00'),
            status='preparing'
        )
        
        response = self.client.post(reverse('cancel_order', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'preparing')  # Status unchanged


class OrderModelTestCase(TestCase):
    """Tests for Order model methods"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='modeluser',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Drinks')
        self.item = MenuItem.objects.create(
            category=self.category,
            name='Coffee',
            price=Decimal('50.00')
        )
    
    def test_token_generation(self):
        """Test that token is auto-generated"""
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00')
        )
        self.assertTrue(order.token_number.startswith('TKN-'))
        self.assertEqual(len(order.token_number), 10)
    
    def test_get_total_items(self):
        """Test get_total_items method"""
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00')
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item,
            item_name='Coffee',
            price=Decimal('50.00'),
            quantity=2
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item,
            item_name='Coffee',
            price=Decimal('50.00'),
            quantity=3
        )
        self.assertEqual(order.get_total_items(), 5)
    
    def test_order_item_subtotal(self):
        """Test OrderItem.get_subtotal method"""
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('150.00')
        )
        item = OrderItem.objects.create(
            order=order,
            menu_item=self.item,
            item_name='Coffee',
            price=Decimal('50.00'),
            quantity=3
        )
        self.assertEqual(item.get_subtotal(), Decimal('150.00'))
