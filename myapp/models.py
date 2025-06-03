from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator
from django.utils.html import format_html
from django.conf import settings
import re

class UserManager(BaseUserManager):
    def create_user(self, username, email, phone_number, password=None):
        if not username:
            raise ValueError('Users must have a username')
        if not email:
            raise ValueError('Users must have an email address')
        
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            phone_number=phone_number,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, phone_number, password):
        user = self.create_user(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
        )
        user.is_staff = True
        user.status = 'active'
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('review', 'Review'),
        ('suspend', 'Suspend'),
    ]
    COUNTRY_CHOICES = [
        ('rwanda', 'Rwanda'),
        ('burundi', 'Burundi'),
        ('kenya', 'Kenya'),
        ('uganda', 'Uganda'),
        ('drc', 'DRC'),
        ('tanzania', 'Tanzania'),
    ]
    country = models.CharField(
        max_length=20,
        choices=COUNTRY_CHOICES,
        default='rwanda',
        db_index=True
    )
    
    username = models.CharField(max_length=30, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    phone_regex = RegexValidator(regex=r'\+?1?\d{9,15}$', 
                                message="Phone number must be entered in the format '+25078xxxxxxx'.")
    phone_number = models.CharField(validators=[phone_regex], max_length=20, unique=True, db_index=True)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='inactive', db_index=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now, db_index=True)
    maintenance_due_date = models.DateField(null=True, blank=True)
    maintenance_paid = models.BooleanField(default=False)
    maintenance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maintenance_paid_date = models.DateField(null=True, blank=True)
    maintenance_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activation_paid_date = models.DateField(null=True, blank=True)
    activation_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']
    
    objects = UserManager()
    
    def __str__(self):
        return self.username

    def colored_status(self):
        if self.status == 'active':
            color = 'green'
        elif self.status == 'inactive':
            color = 'red'
        elif self.status == 'review':
            color = 'orange'
        elif self.status == 'suspend':
            color = 'purple'    
        return format_html('<span style="color: {};">{}</span>', color, self.get_status_display())
    colored_status.short_description = 'Status'

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['status']),
            models.Index(fields=['country']),
        ]

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    referral_code = models.CharField(max_length=30, unique=True, editable=False, db_index=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals', db_index=True)

    # Binary tree structure
    left_leg = models.OneToOneField('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='left_referral', db_index=True)
    right_leg = models.OneToOneField('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='right_referral', db_index=True)

    # Earnings & bonuses
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_withdrawals = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referral_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    retail_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    leadership_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    matching_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # MLM Rank System
    RANKS = [
        ('Starter', 'Starter'),
        ('Silver', 'Silver'),
        ('Gold', 'Gold'),
        ('Platinum', 'Platinum'),
        ('diamond', 'Diamond')
    ]
    rank = models.CharField(max_length=20, choices=RANKS, default='Starter')

    # Tracking bonus awards and matching pairs
    referral_bonus_awarded = models.BooleanField(default=False)
    matching_pairs_count = models.IntegerField(default=0)
    
    # Denormalized field to store the total count of downlines
    cached_downline_count = models.IntegerField(default=0, editable=False)

    @property
    def current_balance(self):
        return (
            self.total_earnings - self.total_withdrawals +
            self.referral_earnings + self.retail_bonus +
            self.leadership_bonus + self.matching_bonus -
            self.total_expenses
        )

    def save(self, *args, **kwargs):
        # Set referral_code if not already set
        if not self.referral_code:
            self.referral_code = self.user.username
        # Update the cached downline count using the iterative method
        self.cached_downline_count = self.compute_downlines_iterative()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

    def compute_downlines_iterative(self):
        """
        Iteratively count all downlines in the binary tree.
        This approach avoids potential recursion issues.
        """
        count = 0
        stack = []
        if self.left_leg:
            stack.append(self.left_leg)
        if self.right_leg:
            stack.append(self.right_leg)
        while stack:
            node = stack.pop()
            count += 1
            if node.left_leg:
                stack.append(node.left_leg)
            if node.right_leg:
                stack.append(node.right_leg)
        return count

    # Overwrite the original count_downlines to use the iterative version
    def count_downlines(self):
        return self.compute_downlines_iterative()

    @property
    def left_count(self):
        """Return 1 if a left referral exists, else 0."""
        return 1 if self.left_leg else 0

    @property
    def right_count(self):
        """Return 1 if a right referral exists, else 0."""
        return 1 if self.right_leg else 0

    @property
    def computed_direct_referrals_count(self):
        """Compute the count of direct referrals dynamically."""
        return self.referrals.count()

def get_default_user():
    """Returns the first available user or None if no users exist"""
    user = User.objects.first()
    return user.id if user else None

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('TOTAL_EARNINGS', 'Total earnings'),
        ('TOTAL_WITHDRAWALS', 'Total Withdrawals'),
        ('REFERRAL_EARNINGS', 'Referral earnings'),
        ('RETAIL_BONUS', 'Retail Bonus'),
        ('LEADERSHIP_BONUS', 'Leadership bonus'),
        ('MATCHING_BONUS', 'Matching bonus'),
        ('TOTAL_EXPENSES', 'Total expenses'),
        ('BALANCE', 'Balance'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        default=get_default_user,
        null=True, blank=True,
        db_index=True
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'No User'} - {self.transaction_type} - {self.amount}"

    def save(self, *args, **kwargs):
        """
        Override save() to wrap the transaction in an atomic block and to create an audit trail.
        If this is a new Transaction, an associated TransactionAudit record will be created.
        """
        from django.db import transaction as db_transaction
        is_new = self.pk is None
        with db_transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                TransactionAudit.objects.create(
                    transaction=self,
                    performed_by=self.user,
                    details=self.description
                )

class TransactionAudit(models.Model):
    """
    Audit trail for transactions.
    This model stores an audit record each time a new Transaction is created.
    """
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='audit')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"Audit for {self.transaction}"

class ActivationFeeProof(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    proof_image = models.ImageField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
            
    def __str__(self):
        return f"{self.full_name} - {self.phone_number}"
    
class AdminNews(models.Model):
    youtube_video_url = models.URLField("YouTube Video URL", max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.youtube_video_url:
            if "youtu.be" in self.youtube_video_url:
                video_id = self.youtube_video_url.split("/")[-1].split("?")[0]
                self.youtube_video_url = f"https://www.youtube.com/embed/{video_id}"
            elif "watch?v=" in self.youtube_video_url:
                self.youtube_video_url = re.sub(r"watch\?v=", "embed/", self.youtube_video_url.split("&")[0])
        super(AdminNews, self).save(*args, **kwargs)

    def __str__(self):
        return self.youtube_video_url or (self.image.url if self.image else "No Video or Image Set")

    def display_content(self):
        if self.youtube_video_url:
            return format_html('<iframe width="560" height="315" src="{}" frameborder="0" allowfullscreen></iframe>', self.youtube_video_url)
        elif self.image:
            return format_html('<img src="{}" width="560" height="315" />', self.image.url)
        return "No content available"
    display_content.short_description = 'Content'
