from decimal import Decimal
from django.db.models import Sum
from django.conf import settings
from payments.models import Commission, Payment, Withdrawal, Deposit
from myapp.models import UserProfile

def process_withdrawal_reversal(withdrawal):
    """Handle withdrawal reversal by refunding user balance"""
    if withdrawal.status == 'completed':
        withdrawal.user.balance += withdrawal.amount
        withdrawal.user.save()
        withdrawal.status = 'reversed'
        withdrawal.save()
        return True
    return False

def process_deposit_addition(deposit):
    """Process successful deposit by adding to user balance"""
    if deposit.status == 'pending':
        deposit.user.balance += deposit.amount
        deposit.user.save()
        deposit.status = 'completed'
        deposit.save()
        return True
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
