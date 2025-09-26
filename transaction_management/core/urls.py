from django.urls import path
from . import views


app_name = "core"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify/", views.verify_otp, name="verify_otp"),
    path("pending/", views.pending_approval, name="pending_approval"),
    path("approvals/", views.approval_list, name="approval_list"),
    path("approvals/approve/<int:profile_id>/", views.approve_profile, name="approve_profile"),
    path("approvals/reject/<int:profile_id>/", views.reject_profile, name="reject_profile"),

]