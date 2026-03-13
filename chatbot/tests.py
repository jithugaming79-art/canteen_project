from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from menu.models import MenuItem, Category
from orders.models import Order, OrderItem
from .rules import find_matching_rule


class ChatbotRuleTest(TestCase):
    """Core rule-based matching tests"""

    def test_exact_greeting(self):
        response, intent, qr = find_matching_rule("hello")
        self.assertEqual(intent, 'greeting')
        self.assertIsNotNone(response)

    def test_exact_greeting_variants(self):
        for word in ['hi', 'hey', 'namaste', 'sup']:
            response, intent, qr = find_matching_rule(word)
            self.assertEqual(intent, 'greeting', f"Failed for: {word}")

    def test_fuzzy_match_typo(self):
        response, intent, qr = find_matching_rule("mennu")
        self.assertEqual(intent, 'menu_overview')

        response, intent, qr = find_matching_rule("pyment")
        self.assertEqual(intent, 'payment_help')

    def test_unknown_message(self):
        response, intent, qr = find_matching_rule("xyzabc123")
        self.assertIsNone(response)
        self.assertIsNone(intent)

    def test_help_command(self):
        response, intent, qr = find_matching_rule("help")
        self.assertEqual(intent, 'help')
        self.assertIn('Menu', response)

    def test_farewell(self):
        response, intent, qr = find_matching_rule("thanks bye")
        self.assertIn(intent, ['farewell'])

    def test_timing_query(self):
        response, intent, qr = find_matching_rule("when is canteen open")
        self.assertEqual(intent, 'timing_query')
        self.assertIn('Mon-Fri', response)


class ChatbotDynamicQueryTest(TestCase):
    """Tests for database-driven dynamic responses"""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Snacks', is_active=True)
        cls.category2 = Category.objects.create(name='Beverages', is_active=True)

        cls.item1 = MenuItem.objects.create(
            name='Veg Burger', category=cls.category, price=45,
            is_available=True, is_vegetarian=True, preparation_time=10,
            is_todays_special=True
        )
        cls.item2 = MenuItem.objects.create(
            name='Chicken Wrap', category=cls.category, price=80,
            is_available=True, is_vegetarian=False, preparation_time=15
        )
        cls.item3 = MenuItem.objects.create(
            name='Cold Coffee', category=cls.category2, price=30,
            is_available=True, is_vegetarian=True, preparation_time=5
        )

    def test_specials_shows_items(self):
        response, intent, qr = find_matching_rule("what are today's specials")
        self.assertEqual(intent, 'special_query')
        self.assertIn('Veg Burger', response)

    def test_veg_items(self):
        response, intent, qr = find_matching_rule("show veg items")
        self.assertEqual(intent, 'veg_query')
        self.assertIn('Veg Burger', response)
        self.assertNotIn('Chicken Wrap', response)

    def test_nonveg_items(self):
        response, intent, qr = find_matching_rule("show non-veg items")
        self.assertEqual(intent, 'nonveg_query')
        self.assertIn('Chicken Wrap', response)

    def test_price_range(self):
        response, intent, qr = find_matching_rule("what are the prices")
        self.assertEqual(intent, 'price_query')
        self.assertIn('30', response)  # min price
        self.assertIn('80', response)  # max price

    def test_menu_overview_shows_categories(self):
        response, intent, qr = find_matching_rule("show me the menu")
        self.assertEqual(intent, 'menu_overview')
        self.assertIn('Snacks', response)
        self.assertIn('Beverages', response)

    def test_category_browsing(self):
        response, intent, qr = find_matching_rule("show snacks items")
        self.assertEqual(intent, 'category_browse')
        self.assertIn('Veg Burger', response)

    def test_popular_items(self):
        response, intent, qr = find_matching_rule("what is popular")
        self.assertEqual(intent, 'recommendation')

    def test_new_items(self):
        response, intent, qr = find_matching_rule("show new items")
        self.assertEqual(intent, 'new_items')

    def test_category_list(self):
        response, intent, qr = find_matching_rule("show categories")
        self.assertEqual(intent, 'category_list')
        self.assertIn('Snacks', response)


class ChatbotItemSearchTest(TestCase):
    """Tests for specific item search + price/info queries"""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Main', is_active=True)
        cls.item = MenuItem.objects.create(
            name='Paneer Tikka', category=cls.category, price=120,
            is_available=True, is_vegetarian=True, preparation_time=20,
            description='Grilled paneer with spices'
        )

    def test_item_price_query(self):
        response, intent, qr = find_matching_rule("what is the price of paneer tikka")
        self.assertEqual(intent, 'price_specific')
        self.assertIn('120', response)
        self.assertIn('Paneer Tikka', response)

    def test_item_info_query(self):
        response, intent, qr = find_matching_rule("tell me about paneer tikka")
        self.assertEqual(intent, 'ingredient_specific')
        self.assertIn('Grilled paneer', response)

    def test_item_found_by_partial_name(self):
        response, intent, qr = find_matching_rule("do you have paneer")
        self.assertIn('Paneer Tikka', response)

    def test_item_enriched_response(self):
        """Item response should include prep time"""
        response, intent, qr = find_matching_rule("paneer tikka")
        self.assertIn('20 min', response)


class ChatbotBudgetTest(TestCase):
    """Tests for budget/price filtering"""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='All', is_active=True)
        MenuItem.objects.create(name='Tea', category=cls.category, price=10, is_available=True)
        MenuItem.objects.create(name='Samosa', category=cls.category, price=15, is_available=True)
        MenuItem.objects.create(name='Biryani', category=cls.category, price=120, is_available=True)

    def test_budget_filter(self):
        response, intent, qr = find_matching_rule("items under 50")
        self.assertEqual(intent, 'budget_query')
        self.assertIn('Tea', response)
        self.assertIn('Samosa', response)
        self.assertNotIn('Biryani', response)

    def test_budget_filter_with_rupee(self):
        response, intent, qr = find_matching_rule("show under ₹20")
        self.assertEqual(intent, 'budget_query')
        self.assertIn('Tea', response)
        self.assertIn('Samosa', response)


class ChatbotUserContextTest(TestCase):
    """Tests for user-specific features (orders, wallet)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('testuser', 'test@test.com', 'pass123')
        cls.category = Category.objects.create(name='Food', is_active=True)
        cls.item = MenuItem.objects.create(
            name='Dosa', category=cls.category, price=50, is_available=True
        )

    def _make_request(self):
        factory = RequestFactory()
        request = factory.post('/chat/api/')
        request.user = self.user
        request.session = SessionStore()
        return request

    def test_order_status_no_orders(self):
        request = self._make_request()
        response, intent, qr = find_matching_rule("where is my order", request)
        self.assertEqual(intent, 'track_query')
        self.assertIn("haven't placed", response)

    def test_order_status_with_active_order(self):
        order = Order.objects.create(
            user=self.user, status='preparing',
            total_amount=50, payment_method='cash'
        )
        OrderItem.objects.create(
            order=order, menu_item=self.item,
            item_name='Dosa', price=50, quantity=1
        )
        request = self._make_request()
        response, intent, qr = find_matching_rule("where is my order", request)
        self.assertEqual(intent, 'track_query')
        self.assertIn('Preparing', response)
        self.assertIn('Dosa', response)

    def test_specific_token_lookup(self):
        order = Order.objects.create(
            user=self.user, status='ready',
            total_amount=50, token_number='TKN-ABC123'
        )
        request = self._make_request()
        response, intent, qr = find_matching_rule("check TKN-ABC123", request)
        self.assertEqual(intent, 'order_lookup')
        self.assertIn('Ready', response)

    def test_wallet_balance(self):
        self.user.profile.wallet_balance = 250
        self.user.profile.save()
        request = self._make_request()
        response, intent, qr = find_matching_rule("what's my balance", request)
        self.assertEqual(intent, 'wallet_query')
        self.assertIn('250', response)

    def test_context_followup(self):
        """Session context for follow-up price questions"""
        request = self._make_request()
        request.session['last_item_name'] = 'Dosa'
        request.session['last_item_price'] = 50.0
        response, intent, qr = find_matching_rule("how much is it", request)
        self.assertEqual(intent, 'price_context')
        self.assertIn('Dosa', response)
        self.assertIn('50', response)


class ChatbotQuickReplyTest(TestCase):
    """Tests for quick reply suggestions"""

    def test_greeting_has_quick_replies(self):
        response, intent, qr = find_matching_rule("hello")
        self.assertIsInstance(qr, list)
        self.assertGreater(len(qr), 0)
        # Each quick reply should have label and message
        for reply in qr:
            self.assertIn('label', reply)
            self.assertIn('message', reply)

    def test_unknown_returns_empty_quick_replies(self):
        response, intent, qr = find_matching_rule("xyzabc123random")
        self.assertIsInstance(qr, list)
