from django.conf import settings
from django.db import models

class Reminder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminders")
    title = models.CharField(max_length=255)
    time = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    title = models.CharField(max_length=255)
    amount = models.PositiveIntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount} تومان"

class Discount(models.Model):
    title = models.CharField(max_length=255)
    percent = models.PositiveIntegerField()
    valid_until = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.percent}%)"
