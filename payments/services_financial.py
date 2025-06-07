from decimal import Decimal
from django.db.models import Sum, F
from django.conf import settings
from payments.models import Commission, Payment, Withdrawal, Deposit
from myapp.models import UserProfile

def process_withdrawal_reversal(new_withdrawal, old_withdrawal):
    """Refund the user's balance if a withdrawal is declined."""
    if new_withdrawal.status == 'declined' and old_withdrawal.status != 'declined':
        updated = UserProfile.objects.filter(user=new_withdrawal.user).update(
            balance=F('balance') + new_withdrawal.amount,
            total_withdrawals=F('total_withdrawals') - new_withdrawal.amount,
        )
        return bool(updated)
    return False

def process_deposit_addition(new_deposit, old_deposit):
    """Add deposit amount to the user's balance once approved."""
    if new_deposit.status == 'approved' and old_deposit.status != 'approved':
        updated = UserProfile.objects.filter(user=new_deposit.user).update(
            balance=F('balance') + new_deposit.amount
        )
        return bool(updated)
    return False

class CommissionService:
    """Service for calculating and awarding commissions"""
    
    RETAIL_BONUS_RATE = Decimal('0.10')  # 10% of product price
    LEADERSHIP_BONUS_RATE = Decimal('0.05')  # 5% of team sales
    MATCHING_BONUS_RATE = Decimal('0.02')  # 2% of downline commissions
    
    @classmethod
    def award_retail_bonus(cls, user, payment):
        """Award retail bonus for direct sales"""
        if payment.status == 'completed':
            amount = payment.amount * cls.RETAIL_BONUS_RATE
            Commission.objects.create(
                user=user,
                amount=amount,
                bonus_type='retail',
                payment=payment,
                description=f"Retail bonus for sale of {payment.product}"
            )
            return amount
        return Decimal('0.00')
    
    @classmethod
    def award_leadership_bonus(cls, user, team_sales):
        """Award leadership bonus based on team performance"""
        amount = team_sales * cls.LEADERSHIP_BONUS_RATE
        Commission.objects.create(
            user=user,
            amount=amount,
            bonus_type='leadership',
            description=f"Leadership bonus for team sales of {team_sales} RWF"
        )
        return amount
    
    @classmethod
    def award_matching_bonus(cls, user, downline_commissions):
        """Award matching bonus from downline commissions"""
        amount = downline_commissions * cls.MATCHING_BONUS_RATE
        Commission.objects.create(
            user=user,
            amount=amount,
            bonus_type='matching',
            description=f"Matching bonus from downline commissions of {downline_commissions} RWF"
        )
        return amount
    
    @classmethod
    def calculate_earnings(cls, user):
        """Calculate total earnings and breakdown by bonus type"""
        commissions = Commission.objects.filter(user=user)
        return {
            'total': commissions.aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'retail': commissions.filter(bonus_type='retail').aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'leadership': commissions.filter(bonus_type='leadership').aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'matching': commissions.filter(bonus_type='matching').aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        }
