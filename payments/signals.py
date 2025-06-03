from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Withdrawal, Deposit
from .services_financial import process_withdrawal_reversal, process_deposit_addition

@receiver(pre_save, sender=Withdrawal)
def reverse_withdrawal_if_declined(sender, instance, **kwargs):
    # If this is a new instance, no reversal is needed.
    if not instance.pk:
        return
    
    # Retrieve the previous state of the withdrawal from the database.
    old_instance = sender.objects.get(pk=instance.pk)
    process_withdrawal_reversal(instance, old_instance)

@receiver(pre_save, sender=Deposit)
def add_deposit_to_balance(sender, instance, **kwargs):
    # Only process updates (i.e. not on first creation)
    if not instance.pk:
        return
    
    # Retrieve the previous state of the deposit from the database.
    old_instance = sender.objects.get(pk=instance.pk)
    process_deposit_addition(instance, old_instance)
