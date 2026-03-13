from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_username, user_email
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        """Always allow auto signup for social accounts (skip signup form)."""
        return True

    def pre_social_login(self, request, sociallogin):
        """
        If a user with this email already exists but isn't connected
        to this social account, automatically connect them.
        Also reactivates deactivated accounts.
        """
        # If the social account is already connected, check if user is deactivated
        if sociallogin.is_existing:
            user = sociallogin.user
            if not user.is_active:
                from django.shortcuts import redirect
                from allauth.exceptions import ImmediateHttpResponse
                request.session['reactivate_email'] = user.email
                raise ImmediateHttpResponse(redirect('reactivate_account'))
            return

        # Get the email from the social account
        email = None
        if sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get('email')
        if not email:
            for em in sociallogin.email_addresses:
                email = em.email
                break
        if not email:
            return

        # Check if a user with this email already exists
        try:
            existing_user = User.objects.get(email=email)
            # Reactivate if deactivated
            if not existing_user.is_active:
                from django.shortcuts import redirect
                from allauth.exceptions import ImmediateHttpResponse
                request.session['reactivate_email'] = existing_user.email
                raise ImmediateHttpResponse(redirect('reactivate_account'))
        except User.DoesNotExist:
            return

        # Connect the social account to the existing user
        sociallogin.connect(request, existing_user)

    def populate_user(self, request, sociallogin, data):
        """Populate user fields from social data, auto-generating username from email."""
        user = super().populate_user(request, sociallogin, data)
        email = data.get('email', '')
        if not user.username and email:
            base_username = email.split('@')[0]
            username = base_username
            # Handle duplicate usernames
            import random
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{random.randint(100, 9999)}"
            user_username(user, username)
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        
        # Ensure profile exists and populate from social data
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        extra_data = sociallogin.account.extra_data
        
        # Get name from social account
        if 'name' in extra_data:
            profile.full_name = extra_data.get('name', '')
        elif 'given_name' in extra_data:
            first = extra_data.get('given_name', '')
            last = extra_data.get('family_name', '')
            profile.full_name = f"{first} {last}".strip()
        
        profile.save()
        return user
