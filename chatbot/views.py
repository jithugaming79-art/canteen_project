from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import random
from .rules import find_matching_rule


@require_http_methods(["POST"])
@login_required
def chat_api(request):
    """API endpoint for chatbot — returns response + dynamic quick replies"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'Empty message'}, status=400)

        # Rule-based matching (with request for user context)
        response, intent, quick_replies = find_matching_rule(user_message, request)

        # Default response if no rule matched
        if response is None:
            response = random.choice([
                "I'm not sure about that. Try asking about the **Menu**, **Specials**, or **Orders**! 🤖",
                "Hmm, I didn't get that. Try 'Help' to see what I can do! ℹ️",
                "My brain is still cooking! 🍳 Can you rephrase that?",
                "I can help with Menu, Orders, Wallet, and Canteen info. Type **Help**! 💡"
            ])
            intent = 'unknown'
            quick_replies = [
                {'label': '❓ Help', 'message': 'Help'},
                {'label': '🍔 Menu', 'message': 'Show me the menu'},
                {'label': '⭐ Specials', 'message': "What are today's specials?"},
            ]

        return JsonResponse({
            'response': response,
            'intent': intent,
            'quick_replies': quick_replies or [],
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
