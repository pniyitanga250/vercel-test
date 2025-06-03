from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from .models import Payment, Withdrawal, SupportMessage, Deposit, MaintenancePayment
from products.models import Product
from myapp.models import UserProfile
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def payment_page(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    balance_color = 'green' if user_profile.balance >= product.price else 'red'
    
    if request.method == 'POST':
        logger.debug("Payment form submitted: %s", request.POST)
        payment_method = request.POST.get('payment_method')
        
        # Create a payment record
        payment = Payment.objects.create(
            user=request.user,
            product=product,
            amount=product.price,
            full_name=request.POST.get('full_name'),
            payment_method=payment_method,
            mobile_number=request.POST.get('mobile_number'),
            bank_account=request.POST.get('bank_account'),
            shipping_address=request.POST.get('shipping_address'),
            proof_of_payment=request.FILES.get('proof_of_payment')
        )
        
        # Process balance payment
        if payment_method == 'balance':
            user_balance = Decimal(user_profile.balance)
            product_price = Decimal(product.price)
            logger.debug("User balance: %s, Product price: %s", user_balance, product_price)
            
            if user_balance >= product_price:
                user_profile.balance = user_balance - product_price
                user_profile.total_expenses += product_price
                user_profile.save()
            else:
                payment.delete()
                messages.error(request, 'Insufficient balance')
                return redirect('payment_page', product_id=product.id)
                
        messages.success(request, 'Payment successful')
        return redirect('payment_history')
        
    return render(request, 'payments/payment_page.html', {
        'product': product,
        'payment_methods': Payment.PAYMENT_METHOD_CHOICES,
        'user_profile': user_profile,
        'balance_color': balance_color,
    })


def payment_history(request):
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payments/payment_history.html', {
        'payments': payments
    })

@login_required
def withdraw(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    available_balance = user_profile.balance

    if request.method == 'POST':
        # Prevent multiple pending withdrawal requests
        if Withdrawal.objects.filter(user=request.user, status='pending').exists():
            messages.error(request, "You already have a pending withdrawal request.")
            return redirect('withdraw')
            
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Invalid withdrawal amount.")
            return redirect('withdraw')
        if amount < Decimal('10.00'):
            messages.error(request, "Minimum withdrawal amount is $10.")
            return redirect('withdraw')
        if amount > available_balance:
            messages.error(request, "Insufficient balance for withdrawal.")
            return redirect('withdraw')
        
        # Deduct the amount from the user's balance immediately
        user_profile.balance = available_balance - amount
        user_profile.total_withdrawals += amount  # optional: for computed balance
        user_profile.save()

        # Create the withdrawal request (status defaults to pending)
        Withdrawal.objects.create(user=request.user, amount=amount, status='pending')
        messages.success(request, "Withdrawal request submitted successfully.")
        return redirect('withdraw')
    
    # For GET requests, also fetch withdrawal history and a flag for pending requests.
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by('-requested_at')
    pending_exists = Withdrawal.objects.filter(user=request.user, status='pending').exists()
    return render(request, 'payments/withdraw.html', {
        'available_balance': available_balance,
        'withdrawals': withdrawals,
        'pending_exists': pending_exists,
    })

@login_required
def deposit(request):
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        full_name = request.POST.get('full_name')
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str)
        except Exception:
            messages.error(request, "Invalid deposit amount.")
            return redirect('deposit')

        Deposit.objects.create(
            user=request.user,
            amount=amount,
            full_name=full_name,
            payment_method=payment_method,
            mobile_number=request.POST.get('mobile_number'),
            bank_account=request.POST.get('bank_account'),
            proof_of_payment=request.FILES.get('proof_of_payment'),
        )
        messages.success(request, "Deposit submitted successfully and is pending approval.")
        return redirect('deposit')

    deposits = Deposit.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payments/deposit.html', {'deposits': deposits})

@login_required
def support_thread(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            SupportMessage.objects.create(user=request.user, content=content)
            messages.success(request, "Your support message has been sent.")
            return redirect('support_thread')
        else:
            messages.error(request, "Please enter a message.")
    
    support_messages = SupportMessage.objects.filter(user=request.user).order_by('created_at')
    context = {
        'support_messages': support_messages,
    }
    return render(request, 'payments/support.html', context)

@login_required
def maintenance_fee_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        amount_str = request.POST.get('amount')
        proof_screenshot = request.FILES.get('proof_screenshot')

        # Validate amount
        try:
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect('maintenance_fee')

        # Create a new MaintenancePayment record
        MaintenancePayment.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            amount=amount,
            proof_screenshot=proof_screenshot,
        )

        messages.success(request, "Your maintenance fee proof has been submitted and is pending admin approval.")
        return redirect('maintenance_fee')

    # For GET requests, simply render the form
    return render(request, 'payments/maintenance_fee.html')