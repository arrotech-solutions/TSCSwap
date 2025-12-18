from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

class MpesaTransaction(models.Model):
    """Model to store M-Pesa transaction details"""
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mpesa_transactions'
    )
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account_reference = models.CharField(max_length=50)
    transaction_desc = models.CharField(max_length=100, default='Payment')
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    result_code = models.CharField(max_length=10, blank=True, null=True)
    result_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.phone_number} - {self.amount} - {self.status}"

    def is_successful(self):
        return self.status == 'completed' and self.mpesa_receipt_number is not None

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('M-Pesa Transaction')
        verbose_name_plural = _('M-Pesa Transactions')


class MySubscription(models.Model):
    """Model to track user subscriptions"""
    
    SUBSCRIPTION_TYPES = (
        ('Free', 'Free'),
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='my_subscription'
    )
    start_date = models.DateTimeField(_('Start Date'), default=timezone.now)
    expiry_date = models.DateTimeField(_('Expiry Date'))
    sub_type = models.CharField(
        _('Subscription Type'),
        max_length=20, 
        choices=SUBSCRIPTION_TYPES, 
        default='Free'
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('My Subscription')
        verbose_name_plural = _('My Subscriptions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s {self.get_sub_type_display()} subscription"

    @property
    def is_active(self):
        """Check if subscription is currently active (not expired)"""
        return self.expiry_date > timezone.now()

    @property
    def days_remaining(self):
        """Get number of days remaining in subscription"""
        if not self.is_active:
            return 0
        return (self.expiry_date - timezone.now()).days

    def extend_subscription(self, days=30, sub_type='Standard'):
        """Extend subscription by specified number of days and update type"""
        now = timezone.now()
        
        # If subscription is already active, extend from expiry date
        if self.expiry_date > now:
            self.expiry_date += timezone.timedelta(days=days)
        else:
            self.expiry_date = now + timezone.timedelta(days=days)
        
        # Update subscription type
        self.sub_type = sub_type
        self.save()
        return self.expiry_date

    def cancel_subscription(self):
        """
        Cancel the subscription by setting expiry to now
        Note: This doesnt delete the record, just makes it inactive
        """
        self.expiry_date = timezone.now()
        self.save()

    @classmethod
    def create_from_payment(cls, user, payment, sub_type=None):
        """
        Create or update subscription from successful payment
        
        Args:
            user: The user to create/update subscription for
            payment: The MpesaTransaction object
            sub_type: Type of subscription (Free, Standard, Premium). 
                    If not provided, will be determined from payment amount.
        """
        now = timezone.now()
        # Set subscription to 6 months (180 days)
        expiry_date = now + timezone.timedelta(days=180)
        
        # Debug: Log incoming parameters
        print(f"CREATE_FROM_PAYMENT - User: {user.id}, Sub Type: {sub_type}, Payment Amount: {payment.amount if payment else 'None'}")
        
        # If sub_type is not provided, determine from payment amount
        if sub_type is None and payment:
            try:
                amount = float(payment.amount)
                print(f"CREATE_FROM_PAYMENT - Processing amount: {amount}")
                if amount >= 2.0:
                    sub_type = 'Premium'
                else:
                    sub_type = 'Standard'
                print(f"CREATE_FROM_PAYMENT - Determined type from amount: {sub_type}")
            except (TypeError, ValueError) as e:
                print(f"ERROR - Failed to process payment amount: {e}")
                sub_type = 'Standard'  # Default to Standard on error
        
        # Ensure we have a valid subscription type
        sub_type = sub_type or 'Standard'
        print(f"CREATE_FROM_PAYMENT - Final subscription type: {sub_type}")
        
        # Debug: Print before get_or_create
        print(f"CREATE_FROM_PAYMENT - Creating/updating subscription for user {user.id} with type: {sub_type}")
        
        # Get or create subscription
        subscription, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'expiry_date': expiry_date,
                'sub_type': sub_type
            }
        )
        
        print(f"CREATE_FROM_PAYMENT - {'Created new' if created else 'Updated existing'} subscription: {subscription}")
        
        # If subscription exists, extend it by 6 months
        if not created:
            subscription.extend_subscription(days=180, sub_type=sub_type)
        
        return subscription
