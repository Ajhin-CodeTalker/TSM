from django import forms
from django.contrib.auth.models import User
from .models import Profile


class StudentRegistrationForm(forms.ModelForm):
    # Add custome fields on top of django built-in User model field
    password = forms.CharField(widget=forms.PasswordInput) #password input
    confirm_password = forms.CharField #confirmation of password field
    student_number = forms.CharField(max_length=50) #student number field
    course = forms.CharField(max_length=100, required=True) #course field
    year_level = forms.CharField(max_length=10, required=True) #year level field
    document = forms.FileField(required=True) #uploading document


    class Meta:
        model = User
        #including both user fields and custom field
        fields = ["username", "email", "password", "confirm_password", "course", "year_level", "document"]

    #validating of registration 
    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")

        #checking if password match
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Password Don't Match!!!")
        return cleaned
    
# Form for verifying OTP input
class OTPForm(forms.Form):
    code = forms.CharField(max_length=6)

