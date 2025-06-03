import logging
from decimal import Decimal
from django.db.models import F
from .models import Transaction, UserProfile
logger = logging.getLogger(__name__)

def recalc_balance(profile):
    """
    Recalculate total earnings and balance.
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

def update_profile_on_transaction(profile, transaction_type, amount):
    """
    Atomically update user profile fields based on the transaction type.
    """
    updates = {}
    if transaction_type == 'TOTAL_EARNINGS':
        updates['total_earnings'] = F('total_earnings') + amount
    elif transaction_type == 'TOTAL_WITHDRAWALS':
        updates['total_withdrawals'] = F('total_withdrawals') + amount
    elif transaction_type == 'REFERRAL_EARNINGS':
        updates['referral_earnings'] = F('referral_earnings') + amount
    elif transaction_type == 'RETAIL_BONUS':
        updates['retail_bonus'] = F('retail_bonus') + amount
    elif transaction_type == 'LEADERSHIP_BONUS':
        updates['leadership_bonus'] = F('leadership_bonus') + amount
    elif transaction_type == 'MATCHING_BONUS':
        updates['matching_bonus'] = F('matching_bonus') + amount
    elif transaction_type == 'TOTAL_EXPENSES':
        updates['total_expenses'] = F('total_expenses') + amount
    elif transaction_type == 'BALANCE':
        updates['balance'] = F('balance') + amount

    if updates:
        UserProfile.objects.filter(pk=profile.pk).update(**updates)
        profile.refresh_from_db(fields=list(updates.keys()))
        recalc_balance(profile)

def award_referral_bonus_on_activation(user_instance):
    """
    Award referral bonus when a referred user is activated.
    """
    try:
        profile = user_instance.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user_instance)

    if not profile.referral_bonus_awarded and profile.referred_by:
        referrer_profile = profile.referred_by
        if referrer_profile.user.status == 'active':
            Transaction.objects.create(
                user=referrer_profile.user,
                transaction_type='REFERRAL_EARNINGS',
                amount=10,
                description=f"Direct Referral Bonus for referring {user_instance.username}"
            )
            referrer_profile.referral_earnings += 10
            referrer_profile.save()
            recalc_balance(referrer_profile)
            profile.referral_bonus_awarded = True
            profile.save()
            logger.info(f"Awarded referral bonus to {referrer_profile.user.username} for referring {user_instance.username}")

def count_active_downlines(profile):
    """
    Recursively count active users in downline.
    (For improved performance consider refactoring to an iterative version.)
    """
    if not profile or profile.user.status != 'active':
        return 0
    left_count = count_active_downlines(profile.left_leg) if profile.left_leg else 0
    right_count = count_active_downlines(profile.right_leg) if profile.right_leg else 0
    return 1 + left_count + right_count

def calculate_matching_pairs(user_profile):
    """
    Calculate the number of matching pairs.
    """
    if not user_profile.left_leg or not user_profile.right_leg:
        return 0
    left_count = count_active_downlines(user_profile.left_leg)
    right_count = count_active_downlines(user_profile.right_leg)
    return min(left_count, right_count)

def award_matching_bonus(user_profile):
    """
    Award matching bonus based on new matching pairs formed.
    """
    if not user_profile.left_leg or not user_profile.right_leg:
        return  # Must have both legs
    total_pairs = calculate_matching_pairs(user_profile)
    new_pairs = total_pairs - user_profile.matching_pairs_count
    logger.info(f"User {user_profile.user.username} has {total_pairs} total pairs and {new_pairs} new pairs")
    rank_bonus = {
        'Starter': 1,
        'Silver': 3,
        'Gold': 6,
        'Platinum': 10,
        'diamond': 15
    }
    if new_pairs > 0:
        bonus_rate = rank_bonus.get(user_profile.rank, 500)
        bonus = new_pairs * bonus_rate
        logger.info(f"Awarding {bonus} matching bonus to {user_profile.user.username}")
        Transaction.objects.create(
            user=user_profile.user,
            transaction_type='MATCHING_BONUS',
            amount=bonus,
            description=f"Binary Matching Bonus for {new_pairs} new pair(s)"
        )
        user_profile.matching_bonus += bonus
        user_profile.matching_pairs_count = total_pairs
        user_profile.save()
        recalc_balance(user_profile)
        logger.info(f"Awarded matching bonus of {bonus} to {user_profile.user.username}")

def award_retail_bonus(payment):
    """
    Award retail bonus commissions up to three referral levels when a payment
    is marked as completed or delivered.
    
    Level 1 (Direct Referral): 10% of product price.
    Level 2 (Indirect Referral): 5% of product price.
    Level 3 (Third-Level Referral): 2% of product price.
    """
    # Ensure the payment is associated with a product and user.
    if not payment.product or not payment.user:
        return

    product_price = payment.product.price
    purchaser_profile = payment.user.userprofile
    commissions = []
    
    # Level 1: Direct Referral
    if purchaser_profile.referred_by:
        level1 = purchaser_profile.referred_by
        bonus1 = product_price * Decimal('0.10')
        commissions.append((level1, 1, bonus1))
        
        # Level 2: Indirect Referral
        if level1.referred_by:
            level2 = level1.referred_by
            bonus2 = product_price * Decimal('0.05')
            commissions.append((level2, 2, bonus2))
            
            # Level 3: Third-Level Referral
            if level2.referred_by:
                level3 = level2.referred_by
                bonus3 = product_price * Decimal('0.02')
                commissions.append((level3, 3, bonus3))
    
    # Create Transaction records for each eligible referrer.
    # The signals for Transaction (see :contentReference[oaicite:5]{index=5}) will update the user profile automatically.
    for referrer_profile, level, bonus in commissions:
        Transaction.objects.create(
            user=referrer_profile.user,
            transaction_type='RETAIL_BONUS',
            amount=bonus,
            description=f"Retail bonus (Level {level}) for purchase of {payment.product.name} by {payment.user.username}"
        )
