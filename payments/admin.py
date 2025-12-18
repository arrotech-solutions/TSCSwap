from django.contrib import admin
from .models import MpesaTransaction, MySubscription
# Register your models here.
admin.site.register(MpesaTransaction)
admin.site.register(MySubscription)