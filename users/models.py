from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    phone = models.CharField(max_length=11, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["username", "email"]  # username میتونه اسم کامل باشه
# users/models.py
from django.db import models
from django.utils import timezone
import hashlib

class OTP(models.Model):
    phone = models.CharField(max_length=11, db_index=True)
    otp_hash = models.CharField(max_length=64)  # sha256 hex
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=5)

    @staticmethod
    def hash_otp(code: str):
        return hashlib.sha256(code.encode()).hexdigest()

    def __str__(self):
        return f"OTP for {self.phone} ({self.created_at})"
from django.db import models

class UserProfile(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.phone})"
