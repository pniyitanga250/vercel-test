import logging
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Transaction, UserProfile, User
from payments.models import Payment
from .services import (
    update_profile_on_transaction,
    award_referral_bonus_on_activation,
    award_matching_bonus,
    award_retail_bonus
)

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Transaction)
def update_user_profile_on_save(sender, instance, created, **kwargs):
    if instance.user:
        profile, _ = UserProfile.objects.get_or_create(user=instance.user)
        update_profile_on_transaction(profile, instance.transaction_type, instance.amount)

@receiver(post_delete, sender=Transaction)
def update_user_profile_on_delete(sender, instance, **kwargs):
    if instance.user:
        profile, _ = UserProfile.objects.get_or_create(user=instance.user)
        # Subtract the transaction amount on delete.
        update_profile_on_transaction(profile, instance.transaction_type, -instance.amount)

@receiver(post_save, sender=User)
def handle_user_activation(sender, instance, created, **kwargs):
    # Award referral bonus when a user is activated
    if not created and instance.status == 'active':
        award_referral_bonus_on_activation(instance)

@receiver(post_save, sender=UserProfile)
def update_matching_bonus_on_referral(sender, instance, created, **kwargs):
    # Trigger matching bonus when a new referral is added
    if created and instance.referred_by:
        logger.info(f"New referral detected: {instance.user.username} referred by {instance.referred_by.user.username}")
        award_matching_bonus(instance.referred_by)

@receiver(post_save, sender=User)
def update_matching_bonus_on_activation(sender, instance, **kwargs):
    # Trigger matching bonus when a user is activated
    if instance.status == 'active':
        try:
            user_profile = UserProfile.objects.get(user=instance)
            logger.info(f"User {instance.username} activated. Checking for matching bonus.")
            award_matching_bonus(user_profile)
        except UserProfile.DoesNotExist:
            logger.warning(f"UserProfile not found for {instance.username}.")

@receiver(pre_save, sender=Payment)
def handle_payment_status_change(sender, instance, **kwargs):
    """
    On updates: if the Payment's status is changing to 'completed' or 'delivered'
    (from another status), trigger the retail bonus award.
    """
    if not instance.pk:
        # This is a new Payment; handle in post_save.
        return

    old_instance = sender.objects.get(pk=instance.pk)
    # Check for a status change from a non-awarded state to 'completed'/'delivered'.
    if old_instance.status not in ['completed', 'delivered'] and instance.status in ['completed', 'delivered']:
        award_retail_bonus(instance)

@receiver(post_save, sender=Payment)
def handle_new_payment(sender, instance, created, **kwargs):
    """
    For newly created Payment instances: if the Payment is created with a status of
    'completed' or 'delivered', award the retail bonus.
    """
    if created and instance.status in ['completed', 'delivered']:
        award_retail_bonus(instance)
