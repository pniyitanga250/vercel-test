import uuid
from django.db import models
from django.conf import settings
from products.models import Product

class Payment(models.Model):
    """Model representing payment details."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]
    
    MOMO_PAY = 'momo_pay'
    TIGO_CASH = 'tigo_cash'
    BANK_TRANSFER = 'bank_transfer'
    BALANCE = 'balance'

    PAYMENT_METHOD_CHOICES = [
        (MOMO_PAY, 'MoMo Pay'),
        (TIGO_CASH, 'Tigo Cash'),
        (BANK_TRANSFER, 'Bank Transfer'),
        (BALANCE, 'Balance'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    full_name = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    shipping_address = models.TextField()
    proof_of_payment = models.ImageField(upload_to='payments/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username if self.user else 'No User'} - {self.payment_method} - {self.amount} - {self.transaction_id} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Automatically generate a unique transaction id if not provided
        if not self.transaction_id:
            # Generate a 10-character uppercase unique ID
            self.transaction_id = uuid.uuid4().hex.upper()[0:10]
        super().save(*args, **kwargs)


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"
    
class SupportMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    admin_reply = models.TextField(blank=True, null=True)
    reply_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"SupportMessage from {self.user.username} at {self.created_at}"
    
class Deposit(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    MOMO_PAY = 'momo_pay'
    TIGO_CASH = 'tigo_cash'
    BANK_TRANSFER = 'bank_transfer'

    PAYMENT_METHOD_CHOICES = [
        (MOMO_PAY, 'MoMo Pay'),
        (TIGO_CASH, 'Tigo Cash'),
        (BANK_TRANSFER, 'Bank Transfer'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    full_name = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    proof_of_payment = models.ImageField(upload_to='deposits/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.payment_method} - {self.amount} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex.upper()[0:10]
        super().save(*args, **kwargs)    
        
class MaintenancePayment(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    DECLINED = 'declined'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (DECLINED, 'Declined'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proof_screenshot = models.ImageField(upload_to='maintenance_fees/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"MaintenancePayment by {self.user.username} - {self.amount}"         


class Commission(models.Model):
    """Model representing commission payments to users"""
    RETAIL = 'retail'
    LEADERSHIP = 'leadership'
    MATCHING = 'matching'
    
    BONUS_TYPES = [
        (RETAIL, 'Retail Bonus'),
        (LEADERSHIP, 'Leadership Bonus'),
        (MATCHING, 'Matching Bonus'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bonus_type = models.CharField(max_length=20, choices=BONUS_TYPES)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_bonus_type_display()} - {self.amount} RWF - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
