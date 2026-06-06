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
    role = models.CharField(max_length=50, default="user")
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
# Address Model 
# ===============================
class Address(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='addresses',
        verbose_name='کاربر'
    )
    title = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='عنوان آدرس (مثلاً خانه، محل کار)'
    )
    province = models.CharField(max_length=100, verbose_name='استان')
    city = models.CharField(max_length=100, verbose_name='شهر')
    district = models.CharField(max_length=100, blank=True, verbose_name='منطقه/محله')
    address_detail = models.TextField(verbose_name='آدرس کامل')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='کد پستی')
    phone = models.CharField(max_length=11, blank=True, verbose_name='تلفن تماس')
    is_default = models.BooleanField(default=False, verbose_name='آدرس پیش‌فرض')
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        verbose_name='عرض جغرافیایی'
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        verbose_name='طول جغرافیایی'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'آدرس'
        verbose_name_plural = 'آدرس‌ها'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.user.fullname} - {self.city}"

    def save(self, *args, **kwargs):
        # اگر این آدرس به عنوان پیش‌فرض انتخاب شد، سایر آدرس‌های کاربر را غیرفعال کن
        if self.is_default:
            Address.objects.filter(user=self.user).update(is_default=False)
        super().save(*args, **kwargs)


