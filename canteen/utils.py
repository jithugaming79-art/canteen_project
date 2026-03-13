"""Shared utility functions for the canteen project."""
from django.http import HttpResponse


def redirect_replace(url):
    """Return an HttpResponse that uses JS window.location.replace()
    so the current page is removed from browser history.
    
    Unlike Django's redirect(), this does NOT add a new history entry.
    The browser replaces the current URL in the history stack.
    
    Use this in payment/checkout flows to prevent users from 
    navigating back to intermediate pages (cart, checkout, payment).
    """
    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script>window.location.replace("{url}");</script>
</head><body></body></html>'''
    return HttpResponse(html)
