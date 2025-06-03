from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from payments.models import Commission, Payment
from payments.services_financial import CommissionService

User = get_user_model()

class CommissionTests(TestCase):
    def setUp(self):
        # Create user with required fields
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            phone_number='+250788123456',
            password='testpass123'
        )
        # Then set balance if the model supports it
        if hasattr(self.user, 'balance'):
            self.user.balance = Decimal('1000.00')
            self.user.save()
            
        self.payment = Payment.objects.create(
            user=self.user,
            amount=Decimal('500.00'),
            status='completed',
            payment_method='momo_pay'
        )

    def test_retail_bonus_calculation(self):
        """Test retail bonus is correctly calculated"""
        bonus = CommissionService.award_retail_bonus(self.user, self.payment)
        self.assertEqual(bonus, Decimal('50.00'))  # 10% of 500
        
        commission = Commission.objects.first()
        self.assertEqual(commission.bonus_type, 'retail')
        self.assertEqual(commission.amount, Decimal('50.00'))
        self.assertEqual(commission.payment, self.payment)

    def test_leadership_bonus_calculation(self):
        """Test leadership bonus is correctly calculated"""
        team_sales = Decimal('2000.00')
        bonus = CommissionService.award_leadership_bonus(self.user, team_sales)
        self.assertEqual(bonus, Decimal('100.00'))  # 5% of 2000
        
        commission = Commission.objects.first()
        self.assertEqual(commission.bonus_type, 'leadership')
        self.assertEqual(commission.amount, Decimal('100.00'))

    def test_matching_bonus_calculation(self):
        """Test matching bonus is correctly calculated"""
        downline_commissions = Decimal('1500.00')
        bonus = CommissionService.award_matching_bonus(self.user, downline_commissions)
        self.assertEqual(bonus, Decimal('30.00'))  # 2% of 1500
        
        commission = Commission.objects.first()
        self.assertEqual(commission.bonus_type, 'matching')
        self.assertEqual(commission.amount, Decimal('30.00'))

    def test_earnings_calculation(self):
        """Test total earnings calculation"""
        # Create test commissions
        Commission.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            bonus_type='retail'
        )
        Commission.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            bonus_type='leadership'
        )
        Commission.objects.create(
            user=self.user,
            amount=Decimal('30.00'),
            bonus_type='matching'
        )

        earnings = CommissionService.calculate_earnings(self.user)
        self.assertEqual(earnings['total'], Decimal('180.00'))
        self.assertEqual(earnings['retail'], Decimal('50.00'))
        self.assertEqual(earnings['leadership'], Decimal('100.00'))
        self.assertEqual(earnings['matching'], Decimal('30.00'))

    def test_invalid_payment_status(self):
        """Test no bonus awarded for incomplete payments"""
        self.payment.status = 'pending'
        self.payment.save()
        
        bonus = CommissionService.award_retail_bonus(self.user, self.payment)
        self.assertEqual(bonus, Decimal('0.00'))
        self.assertEqual(Commission.objects.count(), 0)
