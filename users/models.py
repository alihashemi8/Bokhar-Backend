from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


# این کلاس برای ساختن کاربر جدید یا ادمین جدید
class UserManager(BaseUserManager):

    def create_user(self, phone, fullname, password=None):
        if not phone:
            raise ValueError("لطفا شماره موبایل خود را وارد کنید.")
        user = self.model(fullname=fullname, phone=phone)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, fullname, password):
        if not phone:
            raise ValueError("لطفا شماره موبایل خود را وارد کنید.")
        if not password:
            raise ValueError("لطفا رمز خود را وارد کنید.")
        user = self.model(fullname=fullname, phone=phone)
        user.set_password(password)
        user.is_admin = True
        user.save(using=self._db)
        return user


# مدل شخص سازی شده برای کابران
class User(AbstractBaseUser):
    fullname = models.CharField(max_length=100)
    phone = models.CharField(max_length=11, unique=True)
    is_admin = models.BooleanField(default=False)
    role = models.CharField(default="user")

    REQUIRED_FIELDS = ["fullname"]  # سوپر یوزر برای
    USERNAME_FIELD = "phone"  # بر چه اساسی کاربر وارد شه

    objects = UserManager()

    def __str__(self):
        return f"{self.phone}-{self.fullname}"

    # فقط ادمین اجازه داره
    def has_perm(self, perm, obj=None):
        return self.is_admin

    # فقط ادمین اپ‌ها را می‌بیند
    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin

class Address(models.Model):
    street = models.CharField(max_length=250)
    city = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)