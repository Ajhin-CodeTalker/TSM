

from django.conf import settings #import wide project settings
from django.contrib.auth.models import User #built-in user model for authentiction (such as username, email, password)
from django.db import models #defining database models (e.g, tables, etc)
import uuid #
from datetime import datetime, timedelta #handling dates and time


#THis function allows for file uploads
#defines for WHERE the uploaded files goes/stored in media as follows (media/ directory)
# exmple media file path; media/documents/user_5/my_id_card.png
def upload_documents(instance, filename):
    return f"documents/user_{instance.user.id}/{filename}" #will return the file path on where the data is stored


# --------------------------- PROFILING MODEL---------------------------
class Profile(models.Model):
    #allows to only create a one to one relationship
    # one email = one account
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_number = models.CharField(max_length=50, unique=True)
    course = models.CharField(max_length=100, blank=True)
    year_level = models.CharField(max_length=10, blank=True)
    is_verified_email = models.BooleanField(default=False) #OTP verification that will be sent on their respective email
    is_approved_by_registrar = models.BooleanField(default=False) #registrar approval towards the accounts

    #uploading document: COR or student ID
    document = models.FileField(upload_to=upload_documents, null=True, blank=True) #allows the users to send their documents
    submitted_at = models.DateTimeField(null=True, blank=True) #create a time frame

    # function that will search base on the username and student number
    def __str__(self):
        return f"{self.user.username} ({self.student_number})"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return datetime.utcnow() >self.expires_at.replace(tzinfo=None)
    
    def __str__(self):
        return f"OTP for {self.user.email} - {self.code}"