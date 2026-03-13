from django.urls import path
from . import views

urlpatterns = [
    path('menu/', views.menu_view, name='menu'),
    path('menu/<int:item_id>/', views.item_detail, name='item_detail'),
    path('menu/<int:item_id>/review/', views.add_review, name='add_review'),
    path('menu/<int:item_id>/review/delete/', views.delete_review, name='delete_review'),
    path('menu/<int:item_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites'),
    path('api/menu-availability/', views.menu_availability_api, name='menu_availability_api'),
    path('api/search/', views.search_api, name='search_api'),
]

