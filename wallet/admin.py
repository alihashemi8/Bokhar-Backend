from django.contrib import admin

from .models.models import *
from .models.setting_payment_models import *

# Register your models here.
admin.site.register(Wallet)
admin.site.register(Transaction)
admin.site.register(PaymentTerminal)
admin.site.register(PaymentSession)
admin.site.register(PaymentAttempt)
admin.site.register(PaymentWebhookLog)
admin.site.register(TerminalBankAccount)
admin.site.register(TerminalAllowedDomain)
admin.site.register(BankAccount)
admin.site.register(RefundRequest)
admin.site.register(Settlement)
