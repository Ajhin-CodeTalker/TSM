from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from .forms import StudentRegistrationForm, OTPForm
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile, OTP
from django.utils import timezone
from django.core.mail import send_mail
import random
from datetime import timedelta


def generate_otp_code(length=6):
    return "".join(str(random.randint(0,9)) for _ in range(length))


def register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            student_number = form.cleaned_data["student_number"]
            course = form.cleaned_data.get("course", "")
            year_level = form.cleaned_data.get("year_level", "")
            document = request.FILES.get("document")

            #create inactive user
            user = User.objects.create_user(username=username, email=email, password=password, is_active=False)
            #attach profile
            profile = Profile.objects.get(user=user)
            profile.student_number = student_number
            profile.course = course
            profile.year_level = year_level
            profile.document = document
            profile.submitted_at = timezone.now()
            profile.is_verified_email = False
            profile.is_approved_by_registrar = False
            profile.save()

            # Create OTP
            code = generate_otp_code()
            expires = timezone.now() + timedelta(minutes=20)
            OTP.objects.create(user=user, code=code, expires_at=expires)

            # send email
            subject = "Your Verification Code"
            message = f"Hi {username}, your OTP code is {code}. It expires in {expires}. Thank you"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            send_mail(subject, message, from_email,recipient_list, fail_silently=False)

            # save username in session to be used by verify page
            request.session["verify_user_id"] = user.id
            return redirect("code:verify_otp")
        
        # must return something if form is invalid
        return render(request, "core/register.html", {"form": form})
        
    else:
        form = StudentRegistrationForm()
        #allows to always return a response (for GET or invalid type of form)
        return render(request, "core/register.html", {"form": form})
    
def verify_otp(request):
    """ request session 
    
    * allows to get for approval before finalization of the account
    * create a verification of legitmacy of being a student of the campus
    * registrar will track documents before approving the account
    """
    user_id = request.session.get("verify_user_id")
    if not user_id:
        return redirect("code:register")
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            # check last unexpired OTP
            # in-case it double request of OTP
            otp_qs = OTP.objects.filter(user=user, code=code).order_by("-created_at")
            if not otp_qs.exists():
                form.add_error("code", "Invalid code")
            else:
                otp = otp_qs.first()
                if otp.is_expired():
                    form.add_error("code", "Code expired. Request a new Code!")
                else:
                    # marking each profile as verified
                    profile = user.profile
                    profile.is_verified_email = True
                    profile.save()

                    # optionally allows to delete OTP's
                    OTP.objects.filter(user=user).delete()

                    #log user in
                    login(request, user)
                    return redirect("code:pending_approval")
    else:
        form = OTPForm()
    return render(request, "code/verify_otp.html", {"form": form, "email":user.email})




def pending_approval(request):
    """
        This code handles the pending request of the accounts
    
    """

    #after verification, show pending screen until registrar approves
    return render(request, "code/pending_approval.html")

# registrar can view the list of pending verifications
# but this will required the login for the staff
from django.contrib.auth.decorators import user_passes_test

def staff_check(user):
    return user.is_staff or user.is_superuser

@user_passes_test(staff_check)
def approval_list(request):
    profiles = Profile.objects.filter(is_verified_email=True, is_approve_by_registrar=False)
    return render(request, "core/approval_list.html", {"profiles": profiles})

@user_passes_test(staff_check)
def approve_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_approved_by_registrar = True
    profile.save()
    # sending a mail for notifying as approved account
    send_mail(
        "Account Approved",
        f"Hello {profile.user.username}, you account has been approved by the Registrar",
        settings.DEFAULT_FROM_EMAIL,
        [profile.user.email],
        fail_silently=True,
    )
    return redirect("code:approval_list")

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
        {profile.user.email},
        fail_silently=True,
    )
    return redirect("core:approval_list")





"""
CODE MONA UNG FOR URL'S

"""