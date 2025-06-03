from django.core.management.base import BaseCommand
from myapp.models import UserProfile, Transaction

def count_active_downlines(profile):
    """
    Recursively count active nodes in the subtree rooted at the given profile.
    A profile is counted if its associated user status is 'active'.
    """
    if not profile:
        return 0
    count = 0
    if profile.user.status == 'active':
        count += 1
    if profile.left_leg:
        count += count_active_downlines(profile.left_leg)
    if profile.right_leg:
        count += count_active_downlines(profile.right_leg)
    return count

def calculate_matching_pairs(parent):
    """
    Calculate the number of matching pairs for the parent as the minimum of active
    nodes in the left and right subtrees.
    """
    left_count = count_active_downlines(parent.left_leg)
    right_count = count_active_downlines(parent.right_leg)
    return min(left_count, right_count)
def recalc_profile(profile):
    """
    Recalculate the profile's total earnings and balance.
    
    total_earnings = referral_earnings + retail_bonus + leadership_bonus + matching_bonus
    balance = total_earnings - (total_withdrawals + total_expenses)
    """
    profile.total_earnings = (
        profile.referral_earnings +
        profile.retail_bonus +
        profile.leadership_bonus +
        profile.matching_bonus
    )
    profile.balance = profile.total_earnings - (profile.total_withdrawals + profile.total_expenses)
    profile.save(update_fields=['total_earnings', 'balance'])

class Command(BaseCommand):
    help = "Processes parent profiles to award matching bonus for new matching pairs."

    def handle(self, *args, **options):
        # Get parent profiles with both legs assigned and whose own user is active.
        parents = UserProfile.objects.filter(left_leg__isnull=False, right_leg__isnull=False, user__status='active')
        processed = 0
        rank_bonus = {
            'Starter': 500,
            'Silver': 750,
            'Gold': 1000,
            'Platinum': 1500,
            'diamond': 1500
        }
        for parent in parents:
            total_pairs = calculate_matching_pairs(parent)
            new_pairs = total_pairs - parent.matching_pairs_count
            self.stdout.write(f"Parent: {parent.user.username} | Total Pairs: {total_pairs} | Already Awarded: {parent.matching_pairs_count} | New Pairs: {new_pairs}")
            if new_pairs > 0:
                bonus_rate = rank_bonus.get(parent.rank, 500)
                bonus = new_pairs * bonus_rate
                Transaction.objects.create(
                    user=parent.user,
                    transaction_type='MATCHING_BONUS',
                    amount=bonus,
                    description=f"Binary Matching Bonus for {new_pairs} new pair(s)"
                )
                parent.matching_bonus += bonus
                parent.matching_pairs_count = total_pairs
                parent.save()
                processed += 1
                self.stdout.write(f"Awarded bonus of {bonus} to {parent.user.username}")
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} parent profiles."))
