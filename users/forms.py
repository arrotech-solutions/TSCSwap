from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.forms import ModelMultipleChoiceField, CheckboxSelectMultiple
from home.models import Level, Subject, MySubject
from .models import MyUser, PersonalProfile

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
        model = PersonalProfile
        fields = ['first_name', 'last_name', 'surname', 'phone', 'gender', 'profile_picture']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required if needed
        self.fields['surname'].required = False
        self.fields['profile_picture'].required = False
        
        # Customize phone field
        self.fields['phone'].required = True
        self.fields['phone'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'e.g. +2547XXXXXXXX',
        })
        self.fields['phone'].help_text = 'Required for notifications and account security.'
        
        # Customize gender field
        self.fields['gender'].required = True
        self.fields['gender'].widget.attrs.update({
            'class': 'mt-2 space-y-2',
        })
        self.fields['gender'].help_text = 'Required for demographic information.'
        
        # Customize profile picture field
        self.fields['profile_picture'].widget.attrs.update({
            'class': 'hidden',
            'accept': 'image/*',
        })
        self.fields['profile_picture'].help_text = 'Upload a profile picture (JPG, PNG, or GIF, max 2MB)'
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError('This field is required.')
        return phone
    
    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if not gender:
            raise forms.ValidationError('This field is required.')
        return gender
    
    def save(self, commit=True):
        # Save the profile
        profile = super().save(commit=False)
        
        # Update the user's first_name and last_name from profile
        if profile.user:
            profile.user.first_name = self.cleaned_data.get('first_name', '')
            profile.user.last_name = self.cleaned_data.get('last_name', '')
            if commit:
                profile.user.save()
        
        if commit:
            profile.save()
            
        return profile

class UserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            'placeholder': 'Leave blank to keep current password',
            'autocomplete': 'new-password'
        })
    )
    # Define fields explicitly to control their behavior
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
        })
    )
    
    tsc_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
        })
    )
    
    id_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
        })
    )
    
    class Meta:
        model = MyUser
        fields = ('email', 'tsc_number', 'id_number', 'is_active', 'is_staff', 'role')
        widgets = {
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-teal-600 focus:ring-teal-500 border-gray-300 rounded',
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-teal-600 focus:ring-teal-500 border-gray-300 rounded',
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values from instance
        if self.instance and self.instance.pk:
            self.fields['email'].initial = self.instance.email
            self.fields['tsc_number'].initial = self.instance.tsc_number
            self.fields['id_number'].initial = self.instance.id_number
            
            # Make sure required fields are set
            if not self.instance.email:
                self.fields['email'].required = True
            if not self.instance.tsc_number:
                self.fields['tsc_number'].required = True
            if not self.instance.id_number:
                self.fields['id_number'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('This field is required.')
            
        # Check if email is already in use by another user
        if MyUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email is already in use.')
            
        return email

    def clean_tsc_number(self):
        tsc_number = self.cleaned_data.get('tsc_number')
        # If tsc_number is empty and the user already has one, keep the existing one
        if not tsc_number and self.instance and self.instance.tsc_number:
            return self.instance.tsc_number
        return tsc_number
        
    def clean_id_number(self):
        id_number = self.cleaned_data.get('id_number')
        if not id_number and not self.instance.id_number:
            raise forms.ValidationError('This field is required.')
        return id_number or self.instance.id_number

class SubjectSelectionForm(forms.Form):
    """Form for selecting subjects for a teacher."""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get the user's level from their profile if available
        user_level = None
        if hasattr(self.user, 'profile') and self.user.profile and self.user.profile.level:
            user_level = self.user.profile.level
        
        # Get all levels for the dropdown
        levels = Level.objects.all().order_by('name')
        level_choices = [('', '---------')] + [(level.id, level.name) for level in levels]
        
        # Add level field with dark mode styling
        self.fields['level'] = forms.ChoiceField(
            choices=level_choices,
            required=True,
            initial=str(user_level.id) if user_level else '',
            widget=forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-600 text-white rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200',
                'hx-get': '/users/api/levels/0/subjects/'.replace('0', '${this.value}'),
                'hx-trigger': 'change',
                'hx-target': '#subjects-container',
                'hx-swap': 'innerHTML',
            }),
            label='Teaching Level'
        )
        
        # Add subjects field with dark mode styling
        if user_level:
            self.fields['subjects'] = forms.ModelMultipleChoiceField(
                queryset=Subject.objects.filter(level=user_level).order_by('name'),
                widget=CheckboxSelectMultiple(attrs={
                    'class': 'mt-2 space-y-2 bg-gray-800 text-white border-gray-600 rounded',
                }),
                required=False,
                label='Select Subjects',
                initial=self.initial.get('subjects', [])
            )
    
    def clean(self):
        cleaned_data = super().clean()
        if 'level' in cleaned_data and not cleaned_data.get('subjects'):
            self.add_error('subjects', 'Please select at least one subject.')
        return cleaned_data

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent transition duration-200'
            }) 