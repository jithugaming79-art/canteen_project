from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from orders.models import Order
from payments.models import Payment, WalletTransaction
from decimal import Decimal
from unittest.mock import patch, MagicMock


class PaymentTestCase(TestCase):
    """Tests for payment functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='payuser',
            password='testpass123'
        )
        # Add wallet balance
        self.user.profile.wallet_balance = Decimal('500.00')
        self.user.profile.save()
        
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('150.00'),
            status='pending'
        )
    
    def test_payment_page(self):
        """Test payment page loads"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('payment_page', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150')  # Total amount
    
    def test_cash_payment(self):
        """Test cash payment processing"""
        self.client.force_login(self.user)
        response = self.client.post(reverse('process_cash_payment', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
        
        # Check payment record
        payment = Payment.objects.filter(order=self.order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.method, 'cash')
        self.assertEqual(payment.status, 'pending')
    
    def test_wallet_payment(self):
        """Test wallet payment processing"""
        self.client.force_login(self.user)
        response = self.client.post(reverse('process_wallet_payment', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 302)
        
        # Check wallet was debited
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.wallet_balance, Decimal('350.00'))
        
        # Check order is paid
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, 'confirmed')
        
        # Check transaction record
        transaction = WalletTransaction.objects.filter(user=self.user).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.transaction_type, 'debit')
    
    def test_wallet_insufficient_balance(self):
        """Test wallet payment with insufficient balance"""
        # Set low balance
        self.user.profile.wallet_balance = Decimal('50.00')
        self.user.profile.save()
        
        self.client.force_login(self.user)
        response = self.client.post(reverse('process_wallet_payment', args=[self.order.id]))
        
        # Should redirect back to payment page
        self.assertRedirects(response, reverse('payment_page', args=[self.order.id]))
        
        # Balance unchanged
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.wallet_balance, Decimal('50.00'))


class StripePaymentTestCase(TestCase):
    """Tests for Stripe payment integration"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='stripeuser',
            password='testpass123',
            email='stripe@test.com'
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('200.00'),
            status='pending'
        )
    
    @patch('payments.views.stripe.checkout.Session.create')
    def test_stripe_checkout_redirect(self, mock_create):
        """Test creating a stripe checkout session"""
        # Mock stripe session object
        mock_session = MagicMock()
        mock_session.url = 'https://checkout.stripe.test/'
        mock_create.return_value = mock_session
        
        self.client.force_login(self.user)
        response = self.client.post(reverse('process_online_payment', args=[self.order.id]))
        
        # Should redirect to stripe checkout url
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.url, 'https://checkout.stripe.test/')
        
        # Verify stripe API was called with correct parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['mode'], 'payment')
    
    @patch('payments.views.stripe.checkout.Session.retrieve')
    def test_stripe_success_paid(self, mock_retrieve):
        """Test successful return from Stripe"""
        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.payment_intent = 'pi_test_123'
        mock_session.id = 'cs_test_abc'
        mock_retrieve.return_value = mock_session
        
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('stripe_success', args=[self.order.id]),
            {'session_id': 'cs_test_abc'}
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to order history
        
        # Order should be paid
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, 'confirmed')
        
        # Payment record should exist
        payment = Payment.objects.filter(order=self.order).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.method, 'stripe')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.transaction_id, 'pi_test_123')
        self.assertEqual(payment.stripe_session_id, 'cs_test_abc')
    
    def test_stripe_success_no_session_id(self):
        """Test stripe_success without session_id parameter"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('stripe_success', args=[self.order.id]))
        
        # Should redirect to payment page
        self.assertRedirects(response, reverse('payment_page', args=[self.order.id]))
    
    def test_stripe_already_paid(self):
        """Test stripe redirect when order is already paid"""
        self.order.is_paid = True
        self.order.save()
        
        self.client.force_login(self.user)
        response = self.client.get(reverse('process_online_payment', args=[self.order.id]))
        
        self.assertEqual(response.status_code, 302)


class WalletTestCase(TestCase):
    """Tests for wallet functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='walletuser',
            password='testpass123'
        )
        self.user.profile.wallet_balance = Decimal('100.00')
        self.user.profile.save()
    
    def test_wallet_view(self):
        """Test wallet balance page"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('wallet'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100')  # Balance amount
    
    def test_add_money(self):
        """Test adding money to wallet"""
        self.client.force_login(self.user)
        response = self.client.post(reverse('add_money_to_wallet'), {'amount': 200})
        
        self.assertEqual(response.status_code, 302)
        
        # Check balance updated
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.wallet_balance, Decimal('300.00'))
        
        # Check transaction record
        transaction = WalletTransaction.objects.filter(
            user=self.user,
            transaction_type='credit'
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('200.00'))


class PaymentModelTestCase(TestCase):
    """Tests for Payment model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='paymodeluser',
            password='testpass123'
        )
        self.order = Order.objects.create(
            user=self.user,
            total_amount=Decimal('100.00')
        )
    
    def test_payment_creation(self):
        """Test payment model creation"""
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('100.00'),
            method='upi',
            status='completed',
            transaction_id='TXN123'
        )
        self.assertEqual(str(payment.amount), '100.00')
        self.assertEqual(payment.method, 'upi')
    
    def test_stripe_payment_creation(self):
        """Test Stripe payment model creation with session ID"""
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('100.00'),
            method='stripe',
            status='completed',
            transaction_id='pi_test_123',
            stripe_session_id='cs_test_abc'
        )
        self.assertEqual(payment.method, 'stripe')
        self.assertEqual(payment.stripe_session_id, 'cs_test_abc')
        self.assertEqual(payment.display_method, 'Stripe')
    
    def test_wallet_transaction_creation(self):
        """Test wallet transaction model"""
        transaction = WalletTransaction.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            transaction_type='credit',
            description='Test top-up'
        )
        self.assertEqual(transaction.transaction_type, 'credit')
        self.assertEqual(transaction.description, 'Test top-up')
