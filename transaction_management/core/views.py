
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import authenticate, login
from .forms import StudentRegistrationForm, OTPForm
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile, OTP
from django.utils import timezone
from django.core.mail import send_mail
import random
from datetime import timedelta
from django.db import IntegrityError
# from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AppointmentForms
from django.contrib import messages
from .models import Appointment, Profile
from django.utils import timezone
from datetime import date
from .forms import CertificateRequestForm
from .models import CertificateRequest
from django.contrib.auth.decorators import login_required
from .forms import RegistrarRegistrationForm
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache
from .models import AdminProfile
from .forms import AdminRegistrationForm
from .utils import get_user_role
from .models import RegistrarProfile
from django.contrib.auth import logout

@never_cache
@login_required
def student_dashboard(request):
    """
    Student landing page after registration or login
    shows quick links and status summary
    """

    # Allow open access for testing
    user = request.user if request.user.is_authenticated else None
    profile = None
    appointments = []
    certificates = []
    account_status = "Unverified"

    # Get student profile if logged in
    if user:
        try:
            profile = Profile.objects.get(user=user)
            if profile.is_approved_by_registrar:
                account_status = None  # No need to show anything
            elif not profile.is_verified_email:
                account_status = "Please verify your email to activate your account."
            else:
                account_status = "Your account is pending registrar approval."

        except Profile.DoesNotExist:
            profile = None

        # Get student's appointments and certificates if logged in

        appointments = Appointment.objects.filter(student=user).order_by('-created_at')
        certificates = CertificateRequest.objects.filter(student=user).order_by('-requested_at')

    else:
        # For anonymous visitors — no queries using user
        profile = None
        appointments = []
        certificates = []
        account_status = "Guest Access (Testing Mode)"

    context = {
        "profile": profile,
        "appointments": appointments,
        "certificates": certificates,
        "account_status": account_status,
    }

    return render(request, "core/student_dashboard.html", context)

def register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                is_active=False  # user cannot login yet
            )

            # Staff status
            user.is_staff = False
            user.save()

            Profile.objects.create(
                user=user,
                student_number=form.cleaned_data["student_number"],
                course=form.cleaned_data["course"],
                year_level=form.cleaned_data["year_level"],
                document=request.FILES.get("document"),
                submitted_at=timezone.now(),
                is_verified_email=True,  # always true since no OTP
                is_approved_by_registrar=False

            )

            # direct redirect to pending page
            # login(request, user)  # temporary login to show the page
            return redirect("core:waiting_status", user_id=user.id)

        else:
            print("Form Errors:", form.errors)

    else:
        form = StudentRegistrationForm()

    return render(request, "core/register.html", {"form": form})


@login_required
def waiting_for_approval(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None

    # Handle states
    if profile is None:
        messages.warning(request, "Your account has been created but your profile is incomplete or missing.")
    else:
        if profile.is_verified_email and not profile.is_approved_by_registrar:
            messages.info(request, "Your email is verified! Your account is now waiting for registrar approval.")
        elif not profile.is_verified_email:
            messages.warning(request, "Please verify your email to continue.")
        elif profile.is_approved_by_registrar:
            messages.success(request, "Your account has already been approved!")

    return render(request, "core/waiting_for_approval.html", {
        "profile": profile,
    })
    
def waiting_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(Profile, user=user)

    context = {
        "student": user,
        "profile": profile,
    }
    return render(request, "core/waiting_status.html", context)
# THIS IS THE VIEW FOR THE DASHBOARD/LOGIN MENU
def login_view(request):
    """
    Types of roles that can login for:
    - Students
    - Registrars
    - Admins (superuser)
    """

    if request.method == "POST":
        email_or_username = request.POST.get("email")
        password = request.POST.get("password")

        # login is possible for username or gmail/email
        try:
            user_obj = User.objects.get(email=email_or_username)
            username = user_obj.username
        except User.DoesNotExist:
            username = email_or_username

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # This prevents Django from overriding the redirect of the django administration to the dashboard
            # for superusers and sending them to /admin.
            user.backend = 'django.contrib.auth.backends.ModelBackend'

            login(request, user)

          
     
            # will stll provide a button for /admin access.
            if user.is_superuser:
                messages.success(request, f"Welcome Admin {user.username}!")
                return redirect("core:registrar_dashboard")

            # Registrar / Staff → same dashboard
            if user.is_staff:
                messages.success(request, f"Welcome Registrar {user.username}!")
                return redirect("core:registrar_dashboard")

            # Student login
            try:
                profile = user.profile

                # Student valid but still pending approval
                if not profile.is_approved_by_registrar:
                    return redirect("core:waiting_for_approval")

            except Profile.DoesNotExist:
                # If no profile exists it will be sent to student dashboard
                pass

            return redirect("core:student_dashboard")

        else:
            messages.error(request, "Invalid email/username or password.")

    return render(request, "core/login.html")



# LOGOUT FRAME
def logout_view(request):
    logout(request)
    return redirect("core:login")

def pending_approval(request):
    """
        This code handles the pending request of the accounts
    
    """

    #after verification, show pending screen until registrar approves
    is_approved = False
    if request.user.is_authenticated:
        try:
            is_approved = request.user.profile.is_approved_by_registrar
        except Profile.DoesNotExist:
            is_approved = False
    return render(request, "core/pending_approval.html", {"is_approved": is_approved})

# registrar can view the list of pending verifications
# but this will required the login for the staff
from django.contrib.auth.decorators import user_passes_test

def staff_check(user):
    return user.is_staff or user.is_superuser

@user_passes_test(staff_check)
def approval_list(request):
    # display all profiles that have been submitted and are not yet approved yet
    profiles = Profile.objects.filter(is_approved_by_registrar=False).order_by('-submitted_at')
    return render(request, "core/approval_list.html", {"profiles": profiles})

@user_passes_test(staff_check)
def approve_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_approved_by_registrar = True
    profile.save()

    # activate the user account so they can login
    user = profile.user
    user.is_active = True
    user.save()

    # send notification
    send_mail(
        "Account Approved",
        f"Hello {profile.user.get_full_name() or profile.user.username}, your account has been approved by the registrar. You can now login",
        settings.DEFAULT_FROM_EMAIL,
        [profile.user.email],
        fail_silently=True,
    )

    messages.success(request, f"Approved {profile.user.get_full_name() or profile.user.username}")
    return redirect("core:approval_list")

@user_passes_test(staff_check)
def reject_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)

    # option for deactivating user or deleting user's account
    # can be implemented if the user already graduated/transfers
    user = profile.user
    user.is_active = False
    user.save()
    profile.is_approved_by_registrar = False
    profile.save()
    send_mail(
        "Account Rejected",
        f"Hello {profile.user.username}, your account registration has been rejected by the Registrar.",
        settings.DEFAULT_FROM_EMAIL,
        [profile.user.email],
        fail_silently=True,
    )
    return redirect("core:approval_list")


# helping the function to check if the user is staff
def is_registrar(user):
    return user.is_staff # can be adjust to have a custom role system

@login_required
def student_appointments(request):

    user = request.user
    today = date.today()
    # Get all appointments for the logged-in student (or all if not filtered yet)
    appointments = Appointment.objects.all().order_by('-appointment_date', '-appointment_time')


    #allows to check available schedules
    available_times = [
        "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
        "1:00 PM", "2:00 PM", "3:00 PM",
    ]
    
    # booked out slows for selected date 
    selected_date = request.POST.get('appointment_date', None)
    booked_times = []
    if selected_date:
        booked_times = Appointment.objects.filter(
            appointment_date = selected_date
        ).values_list('appointment_time', flat=True)

    if request.method == 'POST':
        form = AppointmentForms(request.POST)
        if form.is_valid():
            appointment_date = form.cleaned_data['appointment_date']
            appointment_time = form.cleaned_data['appointment_time']

            # prvent from double booking by the same student
            if Appointment.objects.filter(student=user, appointment_date=appointment_date).exists():
                messages.error(request, "You already booked an appointment on this date")
                return redirect('core:student_appointments')

            # prevent full schedule for the slow. ONLY allows limited slots
            # only 10 ppl will be included to take appointment in that specific date
            if Appointment.objects.filter(appointment_date=appointment_date).count() >= 10:
                messages.error(request, "All appointment slots for this day are FULL!")
                return redirect('core:student_appointments')
            
            else:
                appointment = form.save(commit=False)
                appointment.student = user
                appointment.status = 'Pending'
                appointment.save()
                messages.success(request, "Appointment Booked Successfully!")
                return redirect('core:student_appointments')
        else:
            messages.error(request, "Please coorect the errors below")
    else:
        form = AppointmentForms()

    return render(request, 'core/student_appointments.html', {
        'form': form,
        'appointments': appointments,
        'available_times': available_times,
        'booked_times': booked_times,

    })

@never_cache
# @user_passes_test(is_registrar)
def registrar_appointments(request):
    appointments = Appointment.objects.all().order_by("-created_at")
    return render(request, "core/registrar_appointments.html", {"appointments": appointments})


# Checks the admin user and display in the Dashboard of the student
def update_appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(Appointment, id = appointment_id)
    appointment.status = status # displays the user/registrar

    if status == "Approved":
        appointment.approved_by = request.user
    else:
        appointment.approved_by = None

    appointment.save()

    return redirect("core:registrar_appointments")




# @user_passes_test(is_registrar)
def update_certificate_status(request, cert_id, status):
    cert = get_object_or_404(CertificateRequest, id=cert_id)
    cert.status = status

    # storing who performed the action
    cert.approved_by = request.user

    cert.save()

    messages.success(request, f"Certificate Request {status.lower()} successfully")
    return redirect("core:registrar_certificates")
@never_cache
@login_required(login_url='/login/')
def registrar_dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)

    # Logged-in user profile
    user = request.user
    profile = getattr(user, 'profile', None)
    role = get_user_role(user) # This gets all the role from the DataBase
    # Generate initials (e.g., "AA")
    if user.first_name and user.last_name:
        initials = f"{user.first_name[0]}{user.last_name[0]}".upper()
    else:
        initials = user.username[:2].upper()

    pending_profiles = Profile.objects.filter(
        is_verified_email=True, is_approved_by_registrar=False
    ).count()
    processing_appointments = Appointment.objects.filter(status="Pending").count()
    completed_today = Appointment.objects.filter(
        status="Approved", appointment_date=today
    ).count()
    total_this_month = Appointment.objects.filter(
        created_at__date__gte=month_start
    ).count()

    # Build recent activity list
    recent_profiles = Profile.objects.order_by('-submitted_at')[:3]
    recent_appointments = Appointment.objects.order_by('-created_at')[:3]

    recent_activity = []

    for p in recent_profiles:
        recent_activity.append({
            "type": "Profile",
            "text": f"New student registered: {p.user.get_full_name()} (ID: {p.student_number})",
            "time": p.submitted_at,
        })
    for a in recent_appointments:
        recent_activity.append({
            "type": "Appointment",
            "text": f"{a.purpose} appointment from {a.student.username} ({a.status})",
            "time": a.created_at,
        })

    recent_activity = sorted(recent_activity, key=lambda x: x["time"], reverse=True)[:5]

    context = {
        "pending_profiles": pending_profiles,
        "processing_appointments": processing_appointments,
        "completed_today": completed_today,
        "total_this_month": total_this_month,
        "recent_activity": recent_activity,

        # Added so header displays correctly
        "profile": profile,
        "initials": initials,
        "role": role,
    }

    return render(request, "core/registrar_website.html", context)

@never_cache
# REGISTRAR: Allows to view ll certificate request
def registrar_certificates(request):
    certificates = CertificateRequest.objects.all().order_by("-requested_at")
    return render(request, "core/registrar_certificates.html", {"certificates": certificates})

def certificate_request_view(request):
    user = request.user
    from .models import CertificateRequest

    # If user is not logged in (guest view)
    if not user.is_authenticated:
        # Create a blank form (so you can still see it)
        form = CertificateRequestForm()
        previous_request = []  # no real data for guest
        messages.info(request, "You are viewing as a guest. Please log in to submit a request.")
        return render(request, 'core/certificate_request.html', {
            'form': form,
            'previous_request': previous_request,
            'guest_view': True,
        })

    # --- If logged in user ---
    if request.method == "POST":
        form = CertificateRequestForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.student = user
            certificate.save()
            messages.success(request, "Your certificate request has been submitted successfully!")
            return redirect('core:certificate_request')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CertificateRequestForm()

    # show previous requests only for logged-in users
    previous_request = CertificateRequest.objects.filter(student=user).order_by('-requested_at')

    return render(request, 'core/certificate_request.html', {
        'form': form,
        'previous_request': previous_request,
    })


def admin_register(request):
    if request.method == "POST":
        form = AdminRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            


            """
            user = form.save(commit=False)
            # Hash the password
            user.set_password(form.cleaned_data["password"])
            
            # Make the user an admin
            user.is_staff = True
            user.is_superuser = True
            
            user.save()

            # create admin profile if you are using AdminProfile
            AdminProfile.objects.create(user=user)
            """
            messages.success(request, "Admin account created successfully! Please login.")
            return redirect("core:login")
    else:
        form = AdminRegistrationForm()

    return render(request, "core/admin_register.html", {"form": form})


def is_admin(user):
    return user.is_superuser

def is_registrar(user):
    return user.is_staff and not user.is_superuser




# This is for REGISTRAR REGISTER
def registrar_register(request):
    """Registrar REGISTRATION"""
    # Force logout to any current session
    if request.user.is_authenticated:
        logout(request)

    if request.method == "POST":
        form = RegistrarRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_staff = True # This is the landmark/mark as registrar/staff
            user.save()


            # create registrar profile 
            from .models import RegistrarProfile
            RegistrarProfile.objects.create(user=user, role="Registrar")


            messages.success(request, "Registra account created successfuly. Please proceed to login")
            return redirect("core:login") # Redireting towards the login frame
        
    else:
        form = RegistrarRegistrationForm()

    return render(request, "core/registrar_register.html", {"form": form})


def dashboard(request):
    role = get_user_role(request.user)

    return render(request, "core/dashboard.html", {
        "user_role": role,
    })