from django.shortcuts import redirect
import re

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Avoid redirect loops by skipping the complete_profile page itself,
            # as well as auth paths, static files, admin pages, etc.
            path = request.path_info.lower()
            exempt_paths = ['/complete_profile/', '/logout/', '/admin/', '/staff/', '/kitchen/', '/api/', '/media/', '/static/']
            
            if not any(path.startswith(p) for p in exempt_paths):
                # Ensure user has a profile
                if hasattr(request.user, 'profile'):
                    profile = request.user.profile
                    # Check if student/teacher profile lacks phone or college_id
                    if profile.role in ['student', 'teacher']:
                        # Google accounts have empty college_id or phone
                        if not profile.phone or not profile.college_id:
                            return redirect('complete_profile')
        
        response = self.get_response(request)
        return response
