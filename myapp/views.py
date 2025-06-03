from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q

from collections import deque
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import CustomUserCreationForm
from .models import UserProfile, ActivationFeeProof, AdminNews, Transaction
import logging
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .forms import ProfileUpdateForm
from myapp.models import UserProfile
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from myapp.models import Transaction 

logger = logging.getLogger(__name__)


def home(request):
    logger.debug("Home view accessed.")
    return render(request, 'home.html')


def about(request):
    logger.debug("About view accessed.")
    return render(request, 'about.html')


User = get_user_model()

def check_maintenance_due_date(user):
    """
    Checks if the user's maintenance due date has passed.
    If maintenance_due_date is set and current date >= maintenance_due_date,
    then sets the user's status to 'inactive'.
    Logs a message to the terminal when this check is performed.
    """
    logger.debug(f"Checking maintenance due date for user: {user.username}")
    if user.maintenance_due_date and user.status == 'active':
        current_date = timezone.now().date()
        if current_date >= user.maintenance_due_date:
            logger.info(f"User {user.username} maintenance due date reached ({user.maintenance_due_date}). Setting status to suspend.")
            user.status = 'suspend'
            user.save(update_fields=['status'])
            return True
    return False

def maintenance_due_view(request):
    """
    View to inform the user that their maintenance fee is overdue.
    """
    logger.info(f"User {request.user.username} redirected to maintenance due page.")
    return render(request, 'maintenance_due.html')

@login_required(login_url='login')
def dashboard(request):
    # Run the maintenance check on every dashboard request.
    check_maintenance_due_date(request.user)
    
    # Redirect based on user status.
    if request.user.status == 'inactive':
        messages.error(request, "Your account is not activated. Please complete activation.")
        return redirect('activation')
    elif request.user.status == 'suspend':
        messages.error(request, "Your account has been suspended due to an overdue maintenance fee. Please contact the admin for reactivation.")
        return redirect('maintenance_due')
    
    # If active, continue with dashboard logic.
    user_profile, created = UserProfile.objects.select_related('user').get_or_create(user=request.user)
    news = AdminNews.objects.first()  # Latest admin news entry
    referral_link = f"http://{request.get_host()}/register/?ref={user_profile.referral_code}"
    
    # Function to count total downlines recursively
    def count_downlines(profile):
        count = 0
        if profile.left_leg:
            count += 1 + count_downlines(profile.left_leg)
        if profile.right_leg:
            count += 1 + count_downlines(profile.right_leg)
        return count

    direct_referrals_count = user_profile.referrals.count()
    left_total = 1 + user_profile.left_leg.count_downlines() if user_profile.left_leg else 0
    right_total = 1 + user_profile.right_leg.count_downlines() if user_profile.right_leg else 0
    total_downlines = count_downlines(user_profile)

    # Recent Transactions (if available)
    try:
        from transactions.models import Transaction
        recent_transactions = Transaction.objects.filter(user=request.user).select_related('user').order_by('-timestamp')[:5]
    except ImportError:
        recent_transactions = []

    # Account insights
    activation_status = request.user.status
    last_login = request.user.last_login
    date_joined = request.user.date_joined

    context = {
        'user_profile': user_profile,
        'referral_link': referral_link,
        'news': news,
        'direct_referrals_count': direct_referrals_count,
        'left_total': left_total,
        'right_total': right_total,
        'total_downlines': total_downlines,
        'recent_transactions': recent_transactions,
        'activation_status': activation_status,
        'last_login': last_login,
        'date_joined': date_joined,
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='login')
def my_team_view(request):
    sponsor_id = request.GET.get('sponsor_id')
    if sponsor_id:
        # Get the downline's profile based on the sponsor_id from the query parameter
        user_profile = get_object_or_404(UserProfile, user__id=sponsor_id)
    else:
        # Default to the logged-in user's profile
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'my_team.html', {'user_profile': user_profile})
    

def login_view(request):
    """Handles user login process."""
    logger.debug("Login view accessed.")

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check for maintenance due date to update user status if needed.
            check_maintenance_due_date(user)
            
            if user.status == 'inactive':
                login(request, user)
                messages.success(request, "Your account is not activated. Please complete activation.")
                return redirect('activation')
            elif user.status == 'suspend':
                login(request, user)  # Logging in to display the message.
                messages.success(request, "Your account has been suspended due to an overdue maintenance fee. Please contact the admin for reactivation.")
                return redirect('maintenance_due')
            elif user.status == 'review':
                login(request, user)
                messages.info(request, "Your account is under review. Please wait for approval.")
                return redirect('activation_success')
            elif user.status == 'active':
                login(request, user)
                messages.success(request, "Login successful.")
                return redirect('dashboard')
        else:
            logger.warning(f"Invalid login attempt for username: {username}")
            messages.error(request, "Invalid username or password.")
            return redirect('login')
    return render(request, 'login.html')

def logout_view(request):
    """Handles user logout process."""
    logout(request)
    messages.add_message(request, messages.SUCCESS, "You have been logged out.", extra_tags='alert alert-warning')
    return redirect('login')


def activation_view(request):
    """Handles user activation by uploading proof of activation fee payment."""
    logger.debug(f"User accessing activation view: {request.user}")

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        proof_image = request.FILES.get('proof_image')
        
        activation_proof = ActivationFeeProof(
            user=request.user, 
            full_name=full_name,   
            phone_number=phone_number,
            proof_image=proof_image,
        )
        activation_proof.save()

        # Mark user as review after proof submission
        user_profile = get_object_or_404(UserProfile, user=request.user)
        user_profile.user.status = 'review'
        user_profile.user.save()

        return redirect('activation_success')

    return render(request, 'activation.html')


def activation_success_view(request):
    """
    Displays activation success page.
    The referral bonus awarding is now handled automatically via signals,
    so no bonus logic is needed here.
    """
    logger.debug(f"User accessing activation success view: {request.user}")
    return render(request, 'activation_success.html')


def assign_position(new_profile, referrer_profile):
    """
    Automatically assigns the new user's position in the binary tree.
    
    - If the referrer's left_leg is available, assigns new_profile as left_leg.
    - Else if the right_leg is available, assigns new_profile as right_leg.
    - Otherwise, performs a breadth-first search (spillover) to find the next available slot.
    """
    if not referrer_profile.left_leg:
        referrer_profile.left_leg = new_profile
        referrer_profile.save(update_fields=['left_leg'])
        logger.debug("Assigned %s as LEFT leg of %s",
                     new_profile.user.username, referrer_profile.user.username)
        return
    elif not referrer_profile.right_leg:
        referrer_profile.right_leg = new_profile
        referrer_profile.save(update_fields=['right_leg'])
        logger.debug("Assigned %s as RIGHT leg of %s",
                     new_profile.user.username, referrer_profile.user.username)
        return

    queue = deque([referrer_profile])
    while queue:
        current = queue.popleft()
        if not current.left_leg:
            current.left_leg = new_profile
            current.save(update_fields=['left_leg'])
            logger.debug("Spillover assigned %s as LEFT leg of %s",
                         new_profile.user.username, current.user.username)
            return
        if not current.right_leg:
            current.right_leg = new_profile
            current.save(update_fields=['right_leg'])
            logger.debug("Spillover assigned %s as RIGHT leg of %s",
                         new_profile.user.username, current.user.username)
            return
        if current.left_leg:
            queue.append(current.left_leg)
        if current.right_leg:
            queue.append(current.right_leg)
    logger.info("No available position found in the referral tree for %s", new_profile.user.username)


def register_view(request):
    """Handles user registration process with referral tracking and binary tree position assignment."""
    logger.debug("Register view accessed.")

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)

                # Check if user was referred via a referral link.
                ref_code = request.GET.get('ref')
                referred_by = None
                if ref_code:
                    referred_by = UserProfile.objects.filter(referral_code=ref_code).first()

                user.save()

                # Create UserProfile and link to referrer if available.
                new_profile = UserProfile.objects.create(user=user, referred_by=referred_by)

                # If there is a referrer, assign the new user a position in the binary tree.
                if referred_by:
                    assign_position(new_profile, referred_by)

            messages.success(request, "Registration successful! Please proceed to activation.")
            return redirect('activation')

    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def my_profile_view(request):
    user = request.user
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileUpdateForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect('my_profile')
            else:
                messages.error(request, "Please correct the errors below.")
            password_form = PasswordChangeForm(user)
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was successfully updated!")
                return redirect(request.path_info)
            else:
                messages.error(request, "Please correct the errors below.")
            profile_form = ProfileUpdateForm(instance=user)
    else:
        profile_form = ProfileUpdateForm(instance=user)
        password_form = PasswordChangeForm(user)
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'user_profile': user_profile,
    }
    return render(request, 'my_profile.html', context)


def earning_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')
    return render(request, 'earning_history.html', {'transactions': transactions})

# New AJAX view for real-time search
@login_required
def earning_history_ajax(request):
    query = request.GET.get('search', '')
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')
    if query:
        transactions = transactions.filter(
            Q(description__icontains=query) | Q(transaction_type__icontains=query)
        )
    return render(request, 'partials/_earning_history_rows.html', {'transactions': transactions})