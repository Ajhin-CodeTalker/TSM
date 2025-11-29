from .models import AdminProfile, RegistrarProfile, Profile

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
