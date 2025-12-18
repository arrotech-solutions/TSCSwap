from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from .forms import MyUserCreationForm, MyAuthenticationForm, ProfileEditForm, CustomPasswordChangeForm
from .models import PersonalProfile
from home.models import Level, Subject, MySubject
from home.utils import verify_kra_details

# Create your views here.

def login_view(request):
    if request.user.is_authenticated:
        next_url = request.GET.get('next') or request.POST.get('next')
        return redirect(next_url or 'home:home')  # Updated to use 'home:home' namespace
    
    if request.method == 'POST':
        form = MyAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(next_url or 'home:home')  # Updated to use 'home:home' namespace
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MyAuthenticationForm()

    context = {'form': form, 'next': request.GET.get('next')}
    return render(request, 'users/login.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Clear any existing messages and show only this one
            messages.get_messages(request)
            messages.success(request, f'Account created successfully! Let\'s complete your profile.')
            return redirect('users:profile_completion')  # Redirect to profile completion instead of home
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MyUserCreationForm()
    
    return render(request, 'users/signup.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home:home')

@login_required
def profile_view(request):
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    return render(request, 'users/profile.html', {'profile': profile})

@login_required
def profile_edit_view(request):
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileEditForm(
            request.POST, 
            request.FILES, 
            instance=request.user,
            initial={'phone': profile.phone, 'gender': profile.gender}
        )
        
        if form.is_valid():
            user = form.save(commit=False)
            
            # Handle profile picture upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
            # Handle profile picture clear
            elif form.cleaned_data.get('profile_picture-clear'):
                profile.profile_picture.delete(save=False)
            
            # Update profile fields
            profile.phone = form.cleaned_data.get('phone')
            profile.gender = form.cleaned_data.get('gender')
            
            # Save both user and profile
            user.save()
            profile.save()
            
            # Update session with new profile picture if it exists
            if hasattr(profile, 'profile_picture') and profile.profile_picture:
                request.session['profile_picture'] = profile.profile_picture.url
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile_edit')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileEditForm(
            instance=request.user,
            initial={
                'phone': profile.phone,
                'gender': profile.gender,
                'profile_picture': profile.profile_picture if hasattr(profile, 'profile_picture') else None
            }
        )
    
    return render(request, 'users/profile_edit.html', {'form': form})

def parse_name(full_name):
    """Parse full name into first name, last name, and surname.
    
    Rules:
    - First name: First word
    - Last name: Second word (if exists)
    - Surname: All other words combined (if more than 2 names)
    """
    names = full_name.strip().split()
    if not names:
        return '', '', ''
    
    if len(names) == 1:
        return names[0], '', ''  # Only first name
    elif len(names) == 2:
        return names[0], names[1], ''  # First and last name
    else:
        # First name, last name (second word), and surname (all other names)
        return names[0], names[1], ' '.join(names[2:])

@login_required
def profile_completion_view(request):
    if request.method == 'POST':
        # Check if this is the final submission after verification
        if 'verify_kra' in request.POST:
            # Get form data from hidden fields
            id_number = request.POST.get('id_number', '').strip()
            
            # Get the full name from KRA data
            kra_data = request.session.get('kra_data', {})
            full_name = kra_data.get('name', '').strip()
            
            # Parse the full name
            first_name, last_name, surname = parse_name(full_name)
            
            # Update user model
            user = request.user
            user.id_number = id_number
            user.first_name = first_name
            user.last_name = last_name  # Second name is always the last name
            user.save()
            
            # Update or create personal profile
            profile, created = PersonalProfile.objects.get_or_create(user=user)
            profile.first_name = first_name
            profile.last_name = last_name  # Second name is the last name
            profile.surname = surname      # All other names (if any)
            
            # Store any additional names in other_names field
            if surname:
                profile.other_names = surname
            
            # Save additional KRA data if available
            if 'date_of_birth' in kra_data:
                profile.date_of_birth = kra_data['date_of_birth']
            if 'gender' in kra_data:
                # Ensure gender is a single character (M/F/O)
                gender = str(kra_data['gender']).upper()
                profile.gender = gender[0] if gender else 'O'
                
            profile.save()
            
            # Clean up session data
            if 'kra_data' in request.session:
                del request.session['kra_data']
            
            messages.success(request, 'Profile updated successfully! Please select your teaching level and subjects.')
            return redirect('users:select_teaching_info')
            
        else:
            # Initial form submission - verify KRA details
            id_number = request.POST.get('id_number', '').strip()
            first_name = request.POST.get('first_name', '').strip()

            # Validate required fields
            if not id_number or not first_name:
                messages.error(request, 'Both ID number and first name are required')
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })

            # Verify KRA details
            kra_verification = verify_kra_details(id_number)

            if not kra_verification['success']:
                messages.error(request, f"KRA verification failed: {kra_verification['message']}")
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })

            # Get KRA name and clean it for comparison
            kra_name = kra_verification['data'].get('name', '')
            kra_first_name = kra_name.split()[0].lower() if kra_name else ''

            # Compare first names (case-insensitive)
            if first_name.lower() != kra_first_name:
                messages.error(
                    request,
                    "The first name you entered doesn't match the one on record with TSC . "
                )
                return render(request, 'users/profile_completion.html', {
                    'id_number': id_number,
                    'first_name': first_name
                })
            
            # Store KRA data in session for the final submission
            request.session['kra_data'] = {
                'name': kra_name,
                'id_number': id_number,
                # Add any other KRA data you want to save
            }
            
            # Prepare context for template
            context = {
                'id_number': id_number,
                'first_name': first_name.capitalize(),
                'kra_data': {
                    'name': kra_name,
                    'id_number': id_number,
                },
                'show_verification_modal': True
            }
            return render(request, 'users/profile_completion.html', context)

    return render(request, 'users/profile_completion.html')

@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'users/password_change.html', {'form': form})

from home.models import Swaps, SwapRequests

@login_required
def dashboard(request):
    """User dashboard with overview of user's swaps and requests"""
    user = request.user
    
    # Get active swaps created by the user
    active_swaps_queryset = Swaps.objects.filter(user=user, status=True)
    active_swaps_count = active_swaps_queryset.count()
    
    # Get pending swap requests for the user's swaps
    pending_requests = SwapRequests.objects.filter(swap__user=user, accepted=False, is_active=True).count()
    
    # Check profile completion status
    has_profile = hasattr(user, 'profile')
    
    # Personal Information
    personal_info_complete = has_profile and all([
        user.profile.first_name,
        user.profile.last_name,
        user.profile.phone,
        user.id_number,  # This is on the user model, not profile
        user.tsc_number,  # This is on the user model, not profile
        user.profile.gender,
    ])
    
    # Teaching Information
    teaching_info_complete = False
    if has_profile:
        teaching_info_complete = all([
            user.profile.level,
            user.mysubject_set.exists(),
            user.profile.school  # Check for school instead of county/constituency/ward
        ])
    
    # Profile Picture
    profile_picture_complete = has_profile and bool(user.profile.profile_picture)
    
    # Calculate completion percentage (each section is worth ~33.33%)
    completion_percentage = 0
    if personal_info_complete:
        completion_percentage += 33.33
    if teaching_info_complete:
        completion_percentage += 33.33
    if profile_picture_complete:
        completion_percentage += 33.34  # To ensure it adds up to 100%
        
    # Overall profile complete if all sections are complete
    profile_complete = all([personal_info_complete, teaching_info_complete, profile_picture_complete])
    
    # Get subscription status
    subscription = getattr(user, 'my_subscription', None)
    has_active_subscription = subscription.is_active if subscription else False
    subscription_status = {
        'has_subscription': subscription is not None,
        'is_active': has_active_subscription,
        'type': subscription.sub_type if subscription else 'None',
        'expiry_date': subscription.expiry_date.strftime('%B %d, %Y') if subscription and subscription.expiry_date else 'N/A',
        'days_remaining': subscription.days_remaining if subscription else 0,
    }
    
    context = {
        'user': user,
        'active_swaps': active_swaps_count,
        'active_swaps_queryset': active_swaps_queryset,
        'pending_requests': pending_requests,
        'profile_complete': profile_complete,
        'completion_percentage': int(completion_percentage),
        'personal_info_complete': personal_info_complete,
        'teaching_info_complete': teaching_info_complete,
        'profile_picture_complete': profile_picture_complete,
        'subscription': subscription_status,
    }
    
    return render(request, 'users/dashboard.html', context)

@login_required
def select_teaching_info(request):
    """View for selecting teaching level and subjects"""
    # Get or create the user's profile
    profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    # Check if the user already has a level set
    has_level = hasattr(profile, 'level') and profile.level is not None
    
    if request.method == 'POST':
        level_id = request.POST.get('level')
        subject_ids = request.POST.getlist('subjects')
        
        if not level_id:
            messages.error(request, 'Please select your teaching level.')
        elif not subject_ids:
            messages.error(request, 'Please select at least one subject you teach.')
        else:
            try:
                # Update user's level in personal profile
                level = get_object_or_404(Level, id=level_id)
                profile.level = level
                profile.save()
                
                # Get or create a single MySubject entry for the user
                # First, check if there are multiple and consolidate them
                existing_subjects = MySubject.objects.filter(user=request.user)
                
                if existing_subjects.exists():
                    # If multiple exist, use the first one and delete others
                    my_subject = existing_subjects.first()
                    # Delete any additional MySubject entries
                    if existing_subjects.count() > 1:
                        existing_subjects.exclude(pk=my_subject.pk).delete()
                else:
                    # Create new if none exists
                    my_subject = MySubject.objects.create(user=request.user)
                
                # Clear existing subjects and add new ones
                my_subject.subject.clear()
                for subject_id in subject_ids:
                    subject = get_object_or_404(Subject, id=subject_id, level=level)
                    my_subject.subject.add(subject)
                
                messages.success(request, 'Your teaching information has been saved! Please complete your profile by adding your phone number and TSC number to start getting swap opportunities.')
                return redirect('users:profile_edit')
                
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    
    # GET request or form with errors
    levels = Level.objects.all().order_by('name')
    
    # Get the user's current level and subjects if they exist
    current_level = profile.level if hasattr(profile, 'level') and profile.level else None
    current_subjects = []
    
    # Get all subjects from all MySubject entries for the user
    my_subjects = MySubject.objects.filter(user=request.user)
    for my_subject in my_subjects:
        current_subjects.extend(list(my_subject.subject.values_list('id', flat=True)))
    
    # Remove duplicates while preserving order
    seen = set()
    current_subjects = [x for x in current_subjects if not (x in seen or seen.add(x))]
    
    # Get subjects for the current level or all subjects if no level selected
    if current_level:
        subjects = Subject.objects.filter(level=current_level).order_by('name')
    else:
        subjects = Subject.objects.none()
    
    context = {
        'levels': levels,
        'subjects': subjects,
        'current_level': current_level.id if current_level else None,
        'current_subjects': current_subjects,
        'has_level': has_level  # Use the has_level flag we set earlier
    }
    
    return render(request, 'users/teaching_info.html', context)

@login_required
def get_subjects_for_level(request, level_id):
    """API endpoint to get subjects for a specific level"""
    subjects = Subject.objects.filter(level_id=level_id).order_by('name')
    context = {
        'subjects': [{'id': s.id, 'name': s.name} for s in subjects]
    }
    return JsonResponse(context)