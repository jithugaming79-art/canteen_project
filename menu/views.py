from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
import difflib
from .models import Category, MenuItem, Review, Favorite
from accounts.models import SystemSettings

# Review configuration
MAX_COMMENT_LENGTH = 500
MENU_ITEMS_PER_PAGE = 12


@login_required
def menu_view(request):
    """Display menu with category filter, search, veg filter, and pagination"""
    categories = Category.objects.filter(is_active=True)
    selected_category = request.GET.get('category', '')
    search_query = request.GET.get('q', '')
    veg_only = request.GET.get('veg', '') == 'true'
    nonveg_only = request.GET.get('nonveg', '') == 'true'
    price_max = request.GET.get('price_max', '')
    sort_by = request.GET.get('sort', '')
    rating_filter = request.GET.get('rating', '')
    
    # Fetch and filter items
    items = MenuItem.objects.all()
    if selected_category:
        items = items.filter(category_id=selected_category)
    if veg_only:
        items = items.filter(is_vegetarian=True)
    elif nonveg_only:
        items = items.filter(is_vegetarian=False)
    if price_max:
        try:
            items = items.filter(price__lte=int(price_max))
        except ValueError: pass

    # Apply search filter - production-level ranking
    fuzzy_suggestion = ''
    if search_query:
        query = search_query.strip().lower()
        items = items.filter(is_available=True)
        all_items = list(items.select_related('category')) # Already filtered by category/veg if present
        scored_items = []
        
        for item in all_items:
            score = 0
            name_lower = item.name.lower()
            cat_name = item.category.name.lower() if item.category else ''
            
            # 1. Exact name match
            if name_lower == query: score = 100
            # 2. Name starts with
            elif name_lower.startswith(query): score = 80
            # 3. Any word in name starts with
            elif any(word.startswith(query) for word in name_lower.split()): score = 70
            # 4. Name contains
            elif query in name_lower: score = 60
            # 5. Description or Category contains
            elif query in (item.description.lower() if item.description else '') or query in cat_name:
                score = 40
            
            if score > 0:
                scored_items.append((score, item))
        
        # Fuzzy fallback if no matches
        if not scored_items:
            vocab = set()
            name_map = {}
            for item in all_items:
                for w in item.name.lower().split():
                    vocab.add(w)
                    if w not in name_map: name_map[w] = set()
                    name_map[w].add(item.id)
            
            fuzzy_ids = set()
            for word in query.split():
                close = difflib.get_close_matches(word, list(vocab), n=3, cutoff=0.7)
                for cw in close:
                    fuzzy_ids.update(name_map[cw])
            
            if fuzzy_ids:
                scored_items = [(20, item) for item in all_items if item.id in fuzzy_ids]
                fuzzy_suggestion = f'No exact match for "{search_query}". Showing similar results.'
        
        # Sort and extract items
        scored_items.sort(key=lambda x: (-x[0], not x[1].is_available, x[1].name))
        items = [x[1] for x in scored_items]
        total_results = len(items)
        
        # If searching, we often ignore category filter, but if it's explicitly provided, we can keep it
        # Swiggy/Zomato usually search globally.
    else:
        # Normal selection and ordering if no search query
        items = items.order_by('-is_available', 'category', 'name')
        total_results = items.count()
    
    # Apply rating filter (works on both search results and normal listing)
    if rating_filter:
        try:
            min_rating = float(rating_filter)
            if isinstance(items, list):
                items = [item for item in items if item.average_rating >= min_rating]
            else:
                items = [item for item in items if item.average_rating >= min_rating]
            total_results = len(items)
        except ValueError:
            pass
    
    # Apply sort (works on both search results and normal listing)
    if sort_by == 'rating':
        if isinstance(items, list):
            items.sort(key=lambda x: -x.average_rating)
        else:
            items = sorted(items, key=lambda x: -x.average_rating)
    elif sort_by == 'price_low':
        if isinstance(items, list):
            items.sort(key=lambda x: x.price)
        else:
            items = list(items.order_by('price'))
    elif sort_by == 'price_high':
        if isinstance(items, list):
            items.sort(key=lambda x: -x.price)
        else:
            items = list(items.order_by('-price'))

    # Convert to list if still a queryset
    if not isinstance(items, list):
        items = list(items)
        
    specials = MenuItem.objects.filter(is_todays_special=True, is_available=True)
    
    # Popular items: ordered by actual sales count (for "Popular Right Now" section)
    popular_items = list(MenuItem.objects.filter(
        is_available=True
    ).annotate(sales_count=Count('orderitem')).order_by('-is_todays_special', '-sales_count')[:8])
    
    # Get user's favorite item IDs for heart button state
    user_favorite_ids = []
    if request.user.is_authenticated:
        user_favorite_ids = list(
            Favorite.objects.filter(user=request.user).values_list('menu_item_id', flat=True)
        )
    
    # Check maintenance mode
    settings = SystemSettings.get_settings()
    
    context = {
        'categories': categories,
        'items': items,
        'specials': specials,
        'popular_items': popular_items,
        'selected_category': selected_category,
        'search_query': search_query,
        'veg_only': veg_only,
        'nonveg_only': nonveg_only,
        'price_max': price_max,
        'total_results': total_results,
        'fuzzy_suggestion': fuzzy_suggestion,
        'user_favorite_ids': user_favorite_ids,
        'sort_by': sort_by,
        'rating_filter': rating_filter,
        'maintenance_mode': settings.maintenance_mode,
    }
    return render(request, 'menu/menu.html', context)

@login_required
def item_detail(request, item_id):
    """Show details of a single item with reviews"""
    item = get_object_or_404(MenuItem, id=item_id)
    reviews = item.reviews.all()[:10]  # Latest 10 reviews
    user_review = None
    
    is_favorite = False
    if request.user.is_authenticated:
        user_review = Review.objects.filter(user=request.user, menu_item=item).first()
        is_favorite = Favorite.objects.filter(user=request.user, menu_item=item).exists()
    
    # Check maintenance mode
    settings = SystemSettings.get_settings()
    
    context = {
        'item': item,
        'reviews': reviews,
        'user_review': user_review,
        'is_favorite': is_favorite,
        'maintenance_mode': settings.maintenance_mode,
    }
    return render(request, 'menu/item_detail.html', context)

@login_required
@require_POST
def add_review(request, item_id):
    """Add or update a review for a menu item"""
    item = get_object_or_404(MenuItem, id=item_id)
    
    try:
        rating = int(request.POST.get('rating', 5))
    except (ValueError, TypeError):
        rating = 5
    
    comment = request.POST.get('comment', '').strip()
    
    # Validate rating
    if rating < 1 or rating > 5:
        messages.error(request, 'Rating must be between 1 and 5')
        return redirect('item_detail', item_id=item_id)
    
    # Validate comment length
    if len(comment) > MAX_COMMENT_LENGTH:
        messages.error(request, f'Comment must be under {MAX_COMMENT_LENGTH} characters')
        return redirect('item_detail', item_id=item_id)
    
    # Check if user already reviewed this item
    review, created = Review.objects.update_or_create(
        user=request.user,
        menu_item=item,
        defaults={'rating': rating, 'comment': comment}
    )
    
    if created:
        messages.success(request, 'Review submitted successfully!')
    else:
        messages.success(request, 'Review updated successfully!')
    
    return redirect('item_detail', item_id=item_id)

@login_required
@require_POST
def delete_review(request, item_id):
    """Delete user's review"""
    item = get_object_or_404(MenuItem, id=item_id)
    Review.objects.filter(user=request.user, menu_item=item).delete()
    messages.success(request, 'Review deleted')
    return redirect('item_detail', item_id=item_id)


@login_required
def toggle_favorite(request, item_id):
    """Add or remove item from favorites"""
    item = get_object_or_404(MenuItem, id=item_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, menu_item=item)
    
    if not created:
        favorite.delete()
        is_favorited = False
        msg = f'{item.name} removed from favorites'
    else:
        is_favorited = True
        msg = f'{item.name} added to favorites ❤️'
    
    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'is_favorited': is_favorited, 'message': msg})
    
    messages.success(request, msg)
    next_url = request.GET.get('next', request.META.get('HTTP_REFERER', 'menu'))
    return redirect(next_url)


@login_required
def favorites_list(request):
    """Display user's favorite items"""
    favorites = Favorite.objects.filter(user=request.user).select_related('menu_item', 'menu_item__category')
    user_favorite_ids = list(favorites.values_list('menu_item_id', flat=True))
    return render(request, 'menu/favorites.html', {
        'favorites': favorites,
        'user_favorite_ids': user_favorite_ids,
    })


def menu_availability_api(request):
    """API endpoint that returns current availability status of all menu items.
    Used by the menu page for AJAX polling to provide real-time updates.
    No login required since this is public menu data."""
    items = MenuItem.objects.values_list('id', 'is_available')
    availability = {str(item_id): is_available for item_id, is_available in items}
    return JsonResponse({'availability': availability})

@login_required
def search_api(request):
    """Production-level search API with relevance ranking and fuzzy matching.
    Returns JSON results for AJAX autocomplete.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': [], 'total': 0})

    query_lower = query.lower()
    # Only return available items in search API
    all_items = list(MenuItem.objects.filter(is_available=True).select_related('category'))
    items_by_id = {item.id: item for item in all_items}
    scored_items = []
    seen_ids = set()

    # 1. Immediate Matches (Exact, StartsWith, Contains)
    for item in all_items:
        score = 0
        match_type = ''
        name_lower = item.name.lower()
        cat_name = item.category.name.lower() if item.category else ''
        desc_lower = item.description.lower() if item.description else ''

        if name_lower == query_lower:
            score = 100
            match_type = 'exact'
        elif name_lower.startswith(query_lower):
            score = 80
            match_type = 'starts_with'
        elif any(word.startswith(query_lower) for word in name_lower.split()):
            score = 70
            match_type = 'word_start'
        elif query_lower in name_lower:
            score = 60
            match_type = 'contains'
        elif query_lower in desc_lower or query_lower in cat_name:
            score = 40
            match_type = 'description'

        if score > 0:
            scored_items.append((score, item, match_type))
            seen_ids.add(item.id)

    # 2. Fuzzy Fallback (only if needed or for multi-word robustness)
    if len(scored_items) < 5:
        # Build vocabulary
        vocab = set()
        name_map = {}
        for item in all_items:
            for word in item.name.lower().split():
                if len(word) > 2:
                    vocab.add(word)
                    if word not in name_map: name_map[word] = set()
                    name_map[word].add(item.id)
        
        # Fuzzy match query words
        for q_word in query_lower.split():
            if len(q_word) < 3: continue
            close = difflib.get_close_matches(q_word, list(vocab), n=3, cutoff=0.7)
            for cw in close:
                for item_id in name_map[cw]:
                    if item_id not in seen_ids and item_id in items_by_id:
                        scored_items.append((20, items_by_id[item_id], 'fuzzy'))
                        seen_ids.add(item_id)

    # Sort and rank
    MAX_RESULTS = 8
    scored_items.sort(key=lambda x: (-x[0], not x[1].is_available, x[1].name))
    top_items = scored_items[:MAX_RESULTS]

    results = []
    for score, item, match_type in top_items:
        image_url = item.image.url if item.image else ''
        results.append({
            'id': item.id,
            'name': item.name,
            'price': str(item.price),
            'category': item.category.name if item.category else '',
            'image_url': image_url,
            'is_veg': item.is_vegetarian,
            'is_available': item.is_available,
            'rating': item.average_rating,
            'prep_time': item.preparation_time,
            'match_type': match_type,
            'score': score,
        })

    return JsonResponse({
        'results': results,
        'query': query,
        'total': len(scored_items),
    })

