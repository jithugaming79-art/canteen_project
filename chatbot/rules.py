import re
import difflib
import random
from django.db.models import Count, Min, Max, Avg
from menu.models import MenuItem, Category


# =========================================================
# STATIC RULE DEFINITIONS
# =========================================================
CHATBOT_RULES = [
    {
        'keywords': ['hi', 'hello', 'hey', 'greetings', 'sup', 'hii', 'helo', 'bonjour', 'namaste'],
        'responses': [
            "Hello! 👋 Welcome to CampusBites. How can I help you today?",
            "Hi there! 🍔 Ready to order something delicious?",
            "Hey! How can I assist you with your order?",
            "Greetings! 🍕 What are you craving today?"
        ],
        'intent': 'greeting',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
            {'label': '💰 Wallet', 'message': "What's my balance?"},
        ]
    },
    {
        'keywords': ['i am hungry', 'im hungry', 'hungry', 'starving', 'famished'],
        'responses': [
            "Hungry? 😋 Check out our Specials or grab a quick snack from the Menu!",
            "Starving? We've got you covered! 🍔 Check out the 'Popular' section.",
            "Let's fix that! 🌮 Browse our Menu for some tasty options."
        ],
        'intent': 'menu_query',
        'quick_replies': [
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
            {'label': '🔥 Popular', 'message': 'What is popular?'},
            {'label': '💸 Under ₹50', 'message': 'Show items under 50'},
        ]
    },
    {
        'keywords': ['menu', 'food', 'items', 'list', 'options', 'available', 'what do you have', 'what do you serve'],
        'responses': None,  # Dynamic — will show categories
        'intent': 'menu_overview',
        'quick_replies': []  # Will be set dynamically
    },
    {
        'keywords': ['timing', 'time', 'open', 'close', 'hours', 'when', 'schedule', 'working hours'],
        'responses': [
            "🕐 Canteen Timings:\n• Mon-Fri: 8 AM - 6 PM\n• Saturday: 9 AM - 3 PM\n• Sunday: Closed",
            "We are open Mon-Sat! 📅 Check the schedule:\nMon-Fri: 8-6, Sat: 9-3."
        ],
        'intent': 'timing_query',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
            {'label': '📍 Location', 'message': 'Where is the canteen?'},
        ]
    },
    {
        'keywords': ['order', 'how to order', 'process', 'place order'],
        'responses': [
            "To order:\n1. 📜 Browse Menu\n2. ➕ Add items to Cart\n3. 🛒 Checkout\n4. 💳 Pay",
            "Ordering is easy! Just add items to your cart and checkout. 🛒"
        ],
        'intent': 'order_help',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
        ]
    },
    {
        'keywords': ['payment', 'pay', 'upi', 'cash', 'wallet payment', 'money', 'charges'],
        'responses': [
            "We accept Cash, UPI, and Wallet payments. 💸",
            "You can pay via UPI, Cash at counter, or use your CampusBites Wallet! 💳"
        ],
        'intent': 'payment_help',
        'quick_replies': [
            {'label': '💰 Wallet', 'message': "What's my balance?"},
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
        ]
    },
    {
        'keywords': ['special', 'today', 'offer', 'deal', 'discount', 'todays special'],
        'responses': None,  # Dynamic
        'intent': 'special_query',
        'quick_replies': []
    },
    {
        'keywords': ['veg', 'vegetarian', 'vegan', 'pure veg'],
        'responses': None,  # Dynamic
        'intent': 'veg_query',
        'quick_replies': [
            {'label': '🍔 Full Menu', 'message': 'Show me the menu'},
            {'label': '💸 Under ₹50', 'message': 'Show items under 50'},
        ]
    },
    {
        'keywords': ['non veg', 'non-veg', 'nonveg', 'chicken', 'egg', 'meat', 'fish'],
        'responses': None,  # Dynamic
        'intent': 'nonveg_query',
        'quick_replies': [
            {'label': '🌱 Veg Items', 'message': 'Show veg items'},
            {'label': '🍔 Full Menu', 'message': 'Show me the menu'},
        ]
    },
    {
        'keywords': ['popular', 'best', 'recommend', 'suggest', 'trending', 'top', 'favorite'],
        'responses': None,  # Dynamic
        'intent': 'recommendation',
        'quick_replies': [
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
            {'label': '💸 Budget', 'message': 'Show items under 50'},
        ]
    },
    {
        'keywords': ['price', 'cost', 'expensive', 'cheap', 'budget', 'how much', 'rate'],
        'responses': None,  # Dynamic
        'intent': 'price_query',
        'quick_replies': [
            {'label': '💸 Under ₹30', 'message': 'Show items under 30'},
            {'label': '💸 Under ₹50', 'message': 'Show items under 50'},
            {'label': '💸 Under ₹100', 'message': 'Show items under 100'},
        ]
    },
    {
        'keywords': ['wait', 'long', 'queue', 'time to prepare', 'how long', 'duration', 'preparation'],
        'responses': [
            "Preparation time depends on the item. Check the estimated wait time at checkout! ⏱️",
            "Usually 10-15 mins, but you can see the live estimate at checkout. ⏳"
        ],
        'intent': 'wait_query',
        'quick_replies': [
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
        ]
    },
    {
        'keywords': ['cancel', 'refund', 'return'],
        'responses': [
            "You can cancel pending orders from 'My Orders'. Refunds go to your wallet instantly! 💸",
            "Need to cancel? Go to 'My Orders'. Note: Preparing items cannot be cancelled."
        ],
        'intent': 'cancel_query',
        'quick_replies': [
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
            {'label': '💰 Wallet', 'message': "What's my balance?"},
        ]
    },
    {
        'keywords': ['track', 'status', 'where', 'order status', 'my order'],
        'responses': None,  # Dynamic — will check user's orders
        'intent': 'track_query',
        'quick_replies': []
    },
    {
        'keywords': ['token', 'qr', 'code', 'pickup'],
        'responses': [
            "Show your Token # or QR code at the counter to pickup. 🎫",
            "Keep your Token handy! It's on the Order Details page."
        ],
        'intent': 'token_query',
        'quick_replies': [
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
        ]
    },
    {
        'keywords': ['favourite', 'favorite', 'save', 'wishlist', 'love'],
        'responses': [
            "Tap the ❤️ on items you love to save them to Favorites!",
            "Build your meal wishlist by clicking the heart icon! ❤️"
        ],
        'intent': 'favorite_query',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
        ]
    },
    {
        'keywords': ['location', 'address', 'place', 'find', 'where is canteen'],
        'responses': [
            "📍 Ground Floor, Block A (near Library).",
            "Find us at Block A, Ground Floor! Smell the coffee? ☕"
        ],
        'intent': 'location_query',
        'quick_replies': [
            {'label': '🕐 Timings', 'message': 'When is canteen open?'},
        ]
    },
    {
        'keywords': ['contact', 'call', 'phone', 'email', 'manager', 'complaint'],
        'responses': [
            "📞 Contact Manager: 9876543210 or email help@campusbites.com",
            "Need support? Call us at 9876543210. ☎️"
        ],
        'intent': 'contact_query',
        'quick_replies': []
    },
    {
        'keywords': ['wifi', 'internet', 'password'],
        'responses': [
            "📶 Wi-Fi: `CampusBites_Guest` | Pass: `eatgoodfood`",
            "Need net? Connect to `CampusBites_Guest` (Pass: `eatgoodfood`) 🌐"
        ],
        'intent': 'wifi_query',
        'quick_replies': []
    },
    {
        'keywords': ['allergy', 'gluten', 'dairy', 'nut', 'sugar', 'ingredients', 'contain'],
        'responses': [
            "⚠️ Please check item descriptions or ask staff about allergies.",
            "Contains nuts/dairy? Check the description or ask at the counter!"
        ],
        'intent': 'allergy_query',
        'quick_replies': [
            {'label': '🌱 Veg Items', 'message': 'Show veg items'},
        ]
    },
    {
        'keywords': ['thanks', 'thank', 'bye', 'goodbye', 'cya', 'see you'],
        'responses': [
            "You're welcome! Enjoy! 🍽️",
            "Bye! See you soon! 👋",
            "Happy to help! Bon Appétit! 😋"
        ],
        'intent': 'farewell',
        'quick_replies': []
    },
    {
        'keywords': ['how are you', 'how r u', 'whats up'],
        'responses': [
            "I'm just a bot, but I'm hungry for your orders! 🤖",
            "Doing great! Ready to serve some food? 🍕"
        ],
        'intent': 'how_are_you',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
        ]
    },
    {
        'keywords': ['bad', 'worst', 'horrible', 'hate', 'slow'],
        'responses': [
            "I'm sorry to hear that. 😔 Please contact the manager or leave feedback.",
            "We strive to improve! Please let us know specifically what went wrong."
        ],
        'intent': 'complaint',
        'quick_replies': [
            {'label': '📞 Contact', 'message': 'Contact manager'},
        ]
    },
    {
        'keywords': ['good', 'great', 'awesome', 'nice', 'love it', 'amazing', 'excellent'],
        'responses': [
            "Glad you liked it! ❤️",
            "Thanks! We love serving you! 🎉"
        ],
        'intent': 'compliment',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
        ]
    },
    {
        'keywords': ['help', 'what can you do', 'features', 'commands'],
        'responses': [
            "Here's what I can help with:\n\n"
            "🍔 **Menu** — Browse items by category\n"
            "⭐ **Specials** — Today's special items\n"
            "🔥 **Popular** — Most ordered items\n"
            "💰 **Price** — Check item prices\n"
            "🌱 **Veg/Non-Veg** — Filter by diet\n"
            "💸 **Budget** — \"Items under ₹50\"\n"
            "📦 **Orders** — Track your order status\n"
            "💳 **Wallet** — Check your balance\n"
            "🕐 **Timings** — Canteen hours\n"
            "📍 **Location** — Where to find us\n\n"
            "Just type naturally — I understand typos too! 😉"
        ],
        'intent': 'help',
        'quick_replies': [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
            {'label': '💰 Wallet', 'message': "What's my balance?"},
        ]
    },
    {
        'keywords': ['new', 'newly added', 'latest', 'recent', 'just added'],
        'responses': None,  # Dynamic
        'intent': 'new_items',
        'quick_replies': []
    },
    {
        'keywords': ['category', 'categories', 'sections', 'types'],
        'responses': None,  # Dynamic
        'intent': 'category_list',
        'quick_replies': []
    },
]


# =========================================================
# DYNAMIC RESPONSE FUNCTIONS
# =========================================================

def get_popular_items():
    """Get popular items based on order frequency"""
    items = MenuItem.objects.filter(is_available=True).annotate(
        order_count=Count('orderitem')
    ).order_by('-order_count')[:5]

    if not items or all(getattr(i, 'order_count', 0) == 0 for i in items):
        items = MenuItem.objects.filter(is_available=True).annotate(
            review_count=Count('reviews')
        ).order_by('-review_count')[:5]

    if items:
        item_lines = []
        for item in items:
            rating = item.average_rating
            stars = f" ⭐{rating}" if rating > 0 else ""
            item_lines.append(f"• {item.name} — ₹{item.price}{stars}")
        items_text = '\n'.join(item_lines)
        return random.choice([
            f"🌟 **Top Picks:**\n{items_text}",
            f"🔥 **Most Popular:**\n{items_text}",
        ]), [
            {'label': f'💰 {items[0].name}', 'message': f'Price of {items[0].name}'},
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
        ]
    return "Check our Menu page for the best items! 🍔", []


def get_todays_specials():
    """Get today's specials from database"""
    specials = MenuItem.objects.filter(is_todays_special=True, is_available=True)
    if specials.exists():
        item_lines = []
        for s in specials[:6]:
            rating = s.average_rating
            stars = f" ⭐{rating}" if rating > 0 else ""
            prep = f" ⏱️{s.preparation_time}min" if s.preparation_time else ""
            veg = "🌱" if s.is_vegetarian else "🍗"
            item_lines.append(f"• {veg} {s.name} — ₹{s.price}{stars}{prep}")
        items_text = '\n'.join(item_lines)
        return random.choice([
            f"⭐ **Today's Specials:**\n{items_text}\n\nGrab them while they last!",
            f"🎯 **Fresh Today:**\n{items_text}\n\nDon't miss out! ✨",
        ]), [
            {'label': f'💰 {specials[0].name}', 'message': f'Tell me about {specials[0].name}'},
            {'label': '🔥 Popular', 'message': 'What is popular?'},
        ]
    return "No specific specials today, but our regular menu is full of delights! 🍽️", [
        {'label': '🍔 Menu', 'message': 'Show me the menu'},
        {'label': '🔥 Popular', 'message': 'What is popular?'},
    ]


def get_veg_info():
    """Get vegetarian items"""
    veg_items = MenuItem.objects.filter(is_vegetarian=True, is_available=True)
    count = veg_items.count()
    if count > 0:
        item_lines = []
        for item in veg_items[:6]:
            item_lines.append(f"• 🌱 {item.name} — ₹{item.price}")
        items_text = '\n'.join(item_lines)
        more = f"\n\n...and {count - 6} more!" if count > 6 else ""
        return f"🌱 **Vegetarian Items ({count} available):**\n{items_text}{more}", [
            {'label': '🍗 Non-Veg', 'message': 'Show non-veg items'},
            {'label': '💸 Under ₹50', 'message': 'Veg items under 50'},
        ]
    return "We have plenty of veg options! 🌱 Check the 'Veg Only' filter on the Menu.", []


def get_nonveg_info():
    """Get non-vegetarian items"""
    nonveg_items = MenuItem.objects.filter(is_vegetarian=False, is_available=True)
    count = nonveg_items.count()
    if count > 0:
        item_lines = []
        for item in nonveg_items[:6]:
            item_lines.append(f"• 🍗 {item.name} — ₹{item.price}")
        items_text = '\n'.join(item_lines)
        more = f"\n\n...and {count - 6} more!" if count > 6 else ""
        return f"🍗 **Non-Veg Items ({count} available):**\n{items_text}{more}", [
            {'label': '🌱 Veg', 'message': 'Show veg items'},
        ]
    return "No non-veg items currently available.", []


def get_price_range():
    """Get min/max prices from database"""
    prices = MenuItem.objects.filter(is_available=True).aggregate(
        min_price=Min('price'), max_price=Max('price')
    )
    min_p = prices['min_price']
    max_p = prices['max_price']
    if min_p and max_p:
        return f"💰 Items range from ₹{min_p:.0f} to ₹{max_p:.0f}. Ask me about a specific item for its price!", [
            {'label': '💸 Under ₹30', 'message': 'Show items under 30'},
            {'label': '💸 Under ₹50', 'message': 'Show items under 50'},
            {'label': '💸 Under ₹100', 'message': 'Show items under 100'},
        ]
    return "Check our Menu page for prices! 💰", []


def get_menu_overview():
    """Get overview of all categories with item counts"""
    from django.db.models import Q
    categories = Category.objects.filter(is_active=True).annotate(
        item_count=Count('items', filter=Q(items__is_available=True))
    )
    if categories.exists():
        cat_lines = []
        quick_replies = []
        for cat in categories:
            count = getattr(cat, 'item_count', 0)
            if count > 0:
                cat_lines.append(f"• **{cat.name}** — {count} items")
                if len(quick_replies) < 4:
                    quick_replies.append({'label': f'📂 {cat.name}', 'message': f'Show {cat.name} items'})
        total = MenuItem.objects.filter(is_available=True).count()
        cat_text = '\n'.join(cat_lines)
        return f"🍔 **Our Menu ({total} items available):**\n{cat_text}\n\nAsk about a category to see its items!", quick_replies
    return "Our menu is being updated! Check back soon. 🍽️", []


def get_category_items(category_name):
    """Get items in a specific category"""
    from django.db.models import Q
    categories = Category.objects.filter(is_active=True)

    # Try exact match first
    matched_cat = None
    for cat in categories:
        if cat.name.lower() == category_name.lower():
            matched_cat = cat
            break

    # Fuzzy match
    if not matched_cat:
        for cat in categories:
            if category_name.lower() in cat.name.lower() or cat.name.lower() in category_name.lower():
                matched_cat = cat
                break

    if matched_cat:
        items = MenuItem.objects.filter(category=matched_cat, is_available=True)
        if items.exists():
            item_lines = []
            for item in items[:8]:
                veg = "🌱" if item.is_vegetarian else "🍗"
                rating = item.average_rating
                stars = f" ⭐{rating}" if rating > 0 else ""
                item_lines.append(f"• {veg} {item.name} — ₹{item.price}{stars}")
            items_text = '\n'.join(item_lines)
            more = f"\n\n...and {items.count() - 8} more!" if items.count() > 8 else ""
            return f"📂 **{matched_cat.name}:**\n{items_text}{more}", [
                {'label': f'💰 {items[0].name}', 'message': f'Tell me about {items[0].name}'},
                {'label': '🍔 All Menu', 'message': 'Show me the menu'},
            ]
        return f"No items available in {matched_cat.name} right now.", []
    return None, None


def get_new_items():
    """Get recently added items"""
    new_items = MenuItem.objects.filter(is_available=True).order_by('-created_at')[:5]
    if new_items.exists():
        item_lines = []
        for item in new_items:
            veg = "🌱" if item.is_vegetarian else "🍗"
            item_lines.append(f"• {veg} {item.name} — ₹{item.price}")
        items_text = '\n'.join(item_lines)
        return f"🆕 **Recently Added:**\n{items_text}", [
            {'label': '⭐ Specials', 'message': "What are today's specials?"},
            {'label': '🔥 Popular', 'message': 'What is popular?'},
        ]
    return "No new items recently. Check the full menu! 🍔", []


def get_category_list():
    """List all active categories"""
    categories = Category.objects.filter(is_active=True)
    if categories.exists():
        cat_lines = []
        quick_replies = []
        for cat in categories:
            count = cat.items.filter(is_available=True).count()
            cat_lines.append(f"• **{cat.name}** ({count} items)")
            if len(quick_replies) < 4:
                quick_replies.append({'label': f'📂 {cat.name}', 'message': f'Show {cat.name} items'})
        return f"📋 **Categories:**\n" + '\n'.join(cat_lines), quick_replies
    return "Categories are being set up! 🔧", []


def get_budget_items(max_price):
    """Get items under a given price"""
    items = MenuItem.objects.filter(is_available=True, price__lte=max_price).order_by('price')
    if items.exists():
        item_lines = []
        for item in items[:8]:
            veg = "🌱" if item.is_vegetarian else "🍗"
            item_lines.append(f"• {veg} {item.name} — ₹{item.price}")
        items_text = '\n'.join(item_lines)
        more = f"\n\n...and {items.count() - 8} more!" if items.count() > 8 else ""
        return f"💸 **Items under ₹{max_price:.0f} ({items.count()} found):**\n{items_text}{more}", [
            {'label': '🍔 Full Menu', 'message': 'Show me the menu'},
            {'label': '🔥 Popular', 'message': 'What is popular?'},
        ]
    return f"No items found under ₹{max_price:.0f}. Try a higher budget? 😅", []


def get_order_status(request):
    """Get the user's recent order status"""
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return "Please log in to check your orders! 🔐", []

    from orders.models import Order
    active_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'payment_pending']
    active_orders = Order.objects.filter(
        user=request.user,
        status__in=active_statuses
    ).order_by('-created_at')[:3]

    if active_orders.exists():
        order_lines = []
        for order in active_orders:
            status_emoji = {
                'payment_pending': '💳',
                'pending': '🕐',
                'confirmed': '✅',
                'preparing': '🍳',
                'ready': '🎉',
                'out_for_delivery': '🚀',
            }.get(order.status, '📦')
            items_list = ', '.join([f"{i.quantity}x {i.item_name}" for i in order.items.all()[:3]])
            order_lines.append(
                f"• {status_emoji} **{order.token_number}** — {order.get_status_display()}\n"
                f"  Items: {items_list}\n"
                f"  Total: ₹{order.total_amount}"
            )
        orders_text = '\n'.join(order_lines)
        return f"📦 **Your Active Orders:**\n{orders_text}", [
            {'label': '🍔 Order More', 'message': 'Show me the menu'},
        ]
    else:
        # Show last completed order
        last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if last_order:
            return (
                f"No active orders right now.\n\n"
                f"Your last order was **{last_order.token_number}** "
                f"({last_order.get_status_display()}) — ₹{last_order.total_amount} 📋"
            ), [
                {'label': '🍔 Order Now', 'message': 'Show me the menu'},
            ]
        return "You haven't placed any orders yet! Ready to order? 🍔", [
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
        ]


def get_specific_order_status(token, request):
    """Look up a specific order by token number"""
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return None, None

    from orders.models import Order
    try:
        order = Order.objects.get(token_number=token.upper(), user=request.user)
        status_emoji = {
            'payment_pending': '💳',
            'pending': '🕐',
            'confirmed': '✅',
            'preparing': '🍳',
            'ready': '🎉',
            'out_for_delivery': '🚀',
            'delivered': '📬',
            'collected': '✅',
            'cancelled': '❌',
        }.get(order.status, '📦')
        items_list = '\n'.join([f"  • {i.quantity}x {i.item_name} (₹{i.price})" for i in order.items.all()])
        return (
            f"{status_emoji} **Order {order.token_number}**\n"
            f"Status: **{order.get_status_display()}**\n"
            f"Items:\n{items_list}\n"
            f"Total: ₹{order.total_amount}\n"
            f"Placed: {order.created_at.strftime('%d %b, %I:%M %p')}"
        ), [
            {'label': '📦 All Orders', 'message': 'Where is my order?'},
            {'label': '🍔 Order More', 'message': 'Show me the menu'},
        ]
    except Order.DoesNotExist:
        return f"No order found with token **{token}**. Check 'My Orders' page for your orders.", []


def get_wallet_balance(request):
    """Get wallet balance for logged-in user"""
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return "Please log in to check your wallet! 🔐", []

    try:
        balance = request.user.profile.wallet_balance
        return f"💰 Your wallet balance is **₹{balance:.2f}**", [
            {'label': '🍔 Order Now', 'message': 'Show me the menu'},
            {'label': '📦 My Orders', 'message': 'Where is my order?'},
        ]
    except Exception:
        return "Could not fetch your wallet balance. Try the Wallet page. 💳", []


# =========================================================
# DYNAMIC RESOLVER MAP
# =========================================================
DYNAMIC_RESOLVERS = {
    'recommendation': get_popular_items,
    'special_query': get_todays_specials,
    'veg_query': get_veg_info,
    'nonveg_query': get_nonveg_info,
    'price_query': get_price_range,
    'menu_overview': get_menu_overview,
    'new_items': get_new_items,
    'category_list': get_category_list,
}


def resolve_dynamic_response(rule):
    """Resolve a dynamic response based on the rule's intent"""
    resolver = DYNAMIC_RESOLVERS.get(rule['intent'])
    if resolver:
        result = resolver()
        # Resolvers return (response, quick_replies) tuples
        if isinstance(result, tuple):
            return result[0], result[1]
        return result, rule.get('quick_replies', [])

    # Static responses
    responses = rule.get('responses')
    if isinstance(responses, list):
        return random.choice(responses), rule.get('quick_replies', [])
    return responses, rule.get('quick_replies', [])


# =========================================================
# STOP WORDS & MATCHING LOGIC
# =========================================================
STOP_WORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'done',
    'have', 'had', 'has', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me',
    'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
    'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am',
    'be', 'been', 'being', 'yo', 'u', 'r', 'ur', 'can', 'will', 'would', 'could',
    'show', 'tell', 'give', 'get', 'want', 'need', 'please', 'pls',
}


def search_menu_for_item_intent(message, request=None):
    """
    Smarter search:
    1. Detect item name (exact or partial)
    2. Detect intent (price, ingredients, veg status)
    3. Return enriched response with prep time + rating
    """
    message_lower = message.lower()

    # Identify intent flags
    wants_price = any(x in message_lower for x in ['price', 'cost', 'much', 'charge', 'pay', 'rate'])
    wants_ingredients = any(x in message_lower for x in ['ingredient', 'contain', 'what is in', 'made of', 'describe', 'about'])
    wants_veg_status = any(x in message_lower for x in ['is it veg', 'veg or', 'vegetarian'])

    # Find item
    items = MenuItem.objects.filter(is_available=True)
    sorted_items = sorted(items, key=lambda x: len(x.name), reverse=True)

    found_item = None

    # Exact substring match
    for item in sorted_items:
        if item.name.lower() in message_lower:
            found_item = item
            break

    # Partial keyword match
    if not found_item:
        words = message_lower.split()
        potential_matches = []
        for word in words:
            if len(word) < 3 or word in STOP_WORDS:
                continue
            for item in items:
                if word in item.name.lower():
                    potential_matches.append(item)

        if potential_matches:
            potential_matches.sort(key=lambda x: len(x.name))
            found_item = potential_matches[0]

    if not found_item:
        return None, None, None

    # Save context
    if request:
        request.session['last_item_name'] = found_item.name
        request.session['last_item_price'] = float(found_item.price)
        request.session['last_item_id'] = found_item.id

    # Build enriched info
    rating = found_item.average_rating
    review_count = found_item.review_count
    rating_text = f"⭐ {rating}/5 ({review_count} reviews)" if rating > 0 else "No reviews yet"
    prep_text = f"⏱️ ~{found_item.preparation_time} mins" if found_item.preparation_time else ""
    veg_emoji = "🌱 Veg" if found_item.is_vegetarian else "🍗 Non-Veg"
    category_text = f"📂 {found_item.category.name}" if found_item.category else ""

    quick_replies = [
        {'label': '🍔 Menu', 'message': 'Show me the menu'},
        {'label': '🔥 Popular', 'message': 'What is popular?'},
    ]

    # Specific intent responses
    if wants_price:
        return f"💰 **{found_item.name}** costs **₹{found_item.price}**\n{veg_emoji} | {rating_text} | {prep_text}", 'price_specific', quick_replies

    if wants_ingredients:
        desc = found_item.description or "A delicious item from our kitchen!"
        return (
            f"🍔 **{found_item.name}**\n\n"
            f"{desc}\n\n"
            f"💰 ₹{found_item.price} | {veg_emoji}\n"
            f"{rating_text} | {prep_text}\n"
            f"{category_text}"
        ), 'ingredient_specific', quick_replies

    if wants_veg_status:
        return f"{found_item.name} is **{veg_emoji}**.", 'veg_specific', quick_replies

    # Default: full item card
    return (
        f"✅ **{found_item.name}** — ₹{found_item.price}\n\n"
        f"{veg_emoji} | {category_text}\n"
        f"{rating_text}\n"
        f"{prep_text}"
    ), 'menu_specific', quick_replies


def get_context_response(request):
    """Handle follow-up questions using session context"""
    if request and 'last_item_name' in request.session:
        name = request.session['last_item_name']
        price = request.session['last_item_price']
        return f"The price of **{name}** is **₹{price:.0f}**.", 'price_context', []
    return "I'm not sure which item you're asking about. Can you name it?", 'unknown_context', []


# =========================================================
# MAIN MATCHING FUNCTION
# =========================================================

def find_matching_rule(message, request=None):
    """
    Find matching rule for user message.
    Returns (response_text, intent_str, quick_replies_list)
    """
    message_lower = message.lower().strip()
    words = message_lower.split()

    # 0. Check for specific token lookup (TKN-XXXXXX)
    token_match = re.search(r'tkn-[a-zA-Z0-9]+', message_lower)
    if token_match:
        token = token_match.group(0).upper()
        response, quick_replies = get_specific_order_status(token, request)
        if response:
            return response, 'order_lookup', quick_replies

    # 1. Context follow-ups
    if request and any(x in message_lower for x in ['price of it', 'cost of it', 'how much is it', 'it cost', 'its price']):
        return get_context_response(request)

    # 2. Wallet balance check
    if any(x in message_lower for x in ['balance', 'wallet balance', 'my wallet', 'my balance', 'wallet money']):
        response, quick_replies = get_wallet_balance(request)
        return response, 'wallet_query', quick_replies

    # 3. Order tracking (prioritize over generic 'order' keyword)
    if any(x in message_lower for x in ['my order', 'order status', 'track order', 'where is my', 'check order', 'active order']):
        response, quick_replies = get_order_status(request)
        return response, 'track_query', quick_replies

    # 4. Budget/price filter  — "under 50", "below 30", "items under ₹100"
    budget_match = re.search(r'(?:under|below|less than|within|upto|up to)\s*(?:₹|rs\.?|inr)?\s*(\d+)', message_lower)
    if budget_match:
        max_price = float(budget_match.group(1))
        response, quick_replies = get_budget_items(max_price)
        return response, 'budget_query', quick_replies

    # 5. Healthy/dietary check
    if any(x in message_lower for x in ['healthy', 'diet', 'salad', 'fruit', 'low calorie', 'light']):
        return "🥗 For healthy options, check our Fresh Juices or Sandwiches!", 'diet_query', [
            {'label': '🌱 Veg Items', 'message': 'Show veg items'},
            {'label': '🍔 Menu', 'message': 'Show me the menu'},
        ]

    # 6. Category-specific query — "show me snacks", "breakfast items", "drinks"
    categories = Category.objects.filter(is_active=True)
    for cat in categories:
        if cat.name.lower() in message_lower:
            response, quick_replies = get_category_items(cat.name)
            if response:
                return response, 'category_browse', quick_replies

    # 7. Smart item search (prioritized)
    item_response, item_intent, item_qr = search_menu_for_item_intent(message, request)
    if item_response:
        return item_response, item_intent, item_qr

    # 8. Direct keyword match
    for rule in CHATBOT_RULES:
        for keyword in rule['keywords']:
            if ' ' in keyword:
                if keyword in message_lower:
                    response, quick_replies = resolve_dynamic_response(rule)
                    return response, rule['intent'], quick_replies
            else:
                if keyword in words:
                    response, quick_replies = resolve_dynamic_response(rule)
                    return response, rule['intent'], quick_replies
                elif keyword in message_lower and len(keyword) > 4:
                    response, quick_replies = resolve_dynamic_response(rule)
                    return response, rule['intent'], quick_replies

    # 9. Fuzzy match (typo tolerance)
    all_keywords = {}
    for rule in CHATBOT_RULES:
        for k in rule['keywords']:
            all_keywords[k] = rule

    keyword_list = list(all_keywords.keys())

    for word in words:
        if len(word) < 3 or word in STOP_WORDS:
            continue
        matches = difflib.get_close_matches(word, keyword_list, n=1, cutoff=0.6)
        if matches:
            matched_keyword = matches[0]
            rule = all_keywords[matched_keyword]
            response, quick_replies = resolve_dynamic_response(rule)
            return response, rule['intent'], quick_replies

    return None, None, []
