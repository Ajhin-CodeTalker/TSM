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
