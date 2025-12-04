from .models import AdminProfile, RegistrarProfile, Profile
from django.shortcuts import redirect


def get_user_role(user):
    """
    Returns the role of a user based on which profile exists.
    """
    if hasattr(user, 'adminprofile'):
        return user.adminprofile.role
    elif hasattr(user, 'registrarprofile'):
        return user.registrarprofile.role
    elif hasattr(user, 'profile'):
        # Student
        return "Student"
    else:
        return "Unknown"
    


def header_context(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    # Get Role
    role = get_user_role(user)

    # Create Initials
    if user.first_name and user.last_name:
        initials = f"{user.first_name[0]}{user.last_name[0]}".upper()

    else:
        initials = user.username[:2].upper()


    return{
        "profile": profile,
        "role": role,
        "initials": initials,
    }



def pending_student_redirect(get_response):
    def middleware(request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and not profile.is_approved_by_registrar:
                # Allow only the waiting page
                if request.path != "/waiting-status/":
                    return redirect("core:waiting_for_approval")
        return get_response(request)
    return middleware