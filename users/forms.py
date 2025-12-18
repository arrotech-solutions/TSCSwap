from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from .models import MyUser

class MyUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        max_length=50,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    )
    
    tsc_number = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'TSC Number (optional)',
        })
    )
    
    class Meta:
        model = MyUser
        fields = ('email', 'password1', 'password2')
        
    def save(self, commit=True):
        user = super().save(commit=False)
        # Set tsc_number to None if not provided
        if not self.cleaned_data.get('tsc_number'):
            user.tsc_number = None
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Email Address'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'

class MyAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'autofocus': True, 'placeholder': 'Email'})

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = MyUser
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for profile fields
        if hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['gender'].initial = self.instance.profile.gender
    
    # Add phone field that will be saved to PersonalProfile
    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'e.g. +2547XXXXXXXX',
        }),
        help_text='Required for notifications and account security.'
    )
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'mt-2 space-y-2',
        }),
        help_text='Required for demographic information.'
    )
    
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'hidden',
            'accept': 'image/*',
        }),
        help_text='Upload a profile picture (JPG, PNG, or GIF, max 2MB)'
    )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Get or create the user's profile
        profile, created = PersonalProfile.objects.get_or_create(user=user)
        
        # Update profile fields
        profile.phone = self.cleaned_data.get('phone')
        profile.gender = self.cleaned_data.get('gender')
        
        # Handle profile picture upload
        if 'profile_picture' in self.files:
            profile.profile_picture = self.files['profile_picture']
        # Handle profile picture clear
        elif self.cleaned_data.get('profile_picture-clear'):
            profile.profile_picture.delete(save=False)
        
        if commit:
            user.save()
            profile.save()
            
        return user
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make TSC number required
        self.fields['tsc_number'].required = True
        
        # Set initial values from user's profile
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['gender'].initial = self.instance.profile.gender
            if self.instance.profile.profile_picture:
                self.fields['profile_picture'].initial = self.instance.profile.profile_picture
        
        # Add help text for TSC number
        self.fields['tsc_number'].help_text = 'Your TSC registration number is required to verify your teaching status.'
        
        # Add enctype to form for file uploads
        if 'enctype' not in self.Meta.widgets:
            self.Meta.widgets['enctype'] = 'multipart/form-data'
    
    class Meta:
        model = MyUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'gender', 'tsc_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
                'placeholder': 'Email Address',
                'readonly': 'readonly',
            }),
            'tsc_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
                'placeholder': 'TSC Number',
            }),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Save the user first if committing
        if commit:
            user.save()
            
            # Update or create profile with phone number, gender, and profile picture
            profile, created = user.profile.get_or_create(user=user)
            profile.phone = self.cleaned_data['phone']
            profile.gender = self.cleaned_data['gender']
            
            # Handle profile picture upload
            if 'profile_picture' in self.cleaned_data and self.cleaned_data['profile_picture'] is not None:
                # Delete old profile picture if it exists and is different from the new one
                if profile.profile_picture and profile.profile_picture != self.cleaned_data['profile_picture']:
                    profile.profile_picture.delete(save=False)
                profile.profile_picture = self.cleaned_data['profile_picture']
            
            profile.save()
            
        return user

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200'
            }) 