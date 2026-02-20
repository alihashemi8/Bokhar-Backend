from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


# ===============================
# User Manager
# ===============================
class UserManager(BaseUserManager):
    def create_user(self, phone, fullname, password=None, role="user"):
        if not phone:
            raise ValueError("لطفا شماره موبایل خود را وارد کنید.")
        if not fullname:
            raise ValueError("لطفا نام کامل خود را وارد کنید.")

        user = self.model(phone=phone, fullname=fullname, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, fullname, password):
        if not phone:
            raise ValueError("لطفا شماره موبایل خود را وارد کنید.")
        if not password:
            raise ValueError("لطفا رمز خود را وارد کنید.")

        user = self.model(phone=phone, fullname=fullname, role="admin")
        user.set_password(password)
        user.is_admin = True
        user.save(using=self._db)
        return user


# ===============================
# User Model
# ===============================
class User(AbstractBaseUser, PermissionsMixin):
    fullname = models.CharField(max_length=100)
    phone = models.CharField(max_length=11, unique=True)
    is_admin = models.BooleanField(default=False)
    role = models.CharField(max_length=50, default="user")  # ← اضافه شد
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["fullname"]

    objects = UserManager()

    def __str__(self):
        return f"{self.phone} - {self.fullname}"

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin


# ===============================
# UserProfile (بدون تغییر)
# ===============================
class UserProfile(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.phone})"
