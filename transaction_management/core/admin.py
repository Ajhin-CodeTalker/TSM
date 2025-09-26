# this is the adminstration 

from django.contrib import admin
from .models import Profile, OTP


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student_number", "is_verified_email", "is_approved_by_registrar", "submitted_at")
    list_filter = ("is_verified_email", "is_approved_by_registrar")
    search_fields = ("user__username", "student_number", "user__email")