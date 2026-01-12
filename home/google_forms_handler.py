"""
Google Forms Integration Handler for TSCSwap
Processes form submissions and creates user accounts with all required profiles.
"""

import json
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import (
    Level, Subject, MySubject, Counties, SwapPreference
)
from users.models import PersonalProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class GoogleFormProcessor:
    """Process Google Form submissions and create user accounts."""
    
    def __init__(self, form_data):
        self.form_data = form_data
        self.errors = []
        
    def validate(self):
        """Validate all required fields are present and valid."""
        required_fields = [
            'full_name', 'phone', 'email', 'teacher_level',
            'preferred_counties', 'most_preferred_county'
        ]
        
        for field in required_fields:
            if field not in self.form_data or not self.form_data[field]:
                self.errors.append(f"Missing required field: {field}")
        
        # Validate email format
        email = self.form_data.get('email', '')
        if email and '@' not in email:
            self.errors.append("Invalid email format")
        
        # Validate phone number format (Kenyan format)
        phone = self.form_data.get('phone', '')
        if phone and not (phone.startswith('0') and len(phone) >= 10):
            self.errors.append("Invalid phone number format. Should start with 0 and be at least 10 digits")
        
        # Check if email already exists
        if email and User.objects.filter(email=email).exists():
            self.errors.append(f"User with email {email} already exists")
        
        # Validate subjects for secondary teachers
        teacher_level = self.form_data.get('teacher_level', '')
        subjects = self.form_data.get('subjects', [])
        
        if teacher_level == 'Secondary/High School':
            if not subjects:
                self.errors.append("Secondary teachers must select at least one subject")
            elif len(subjects) > 2:
                self.errors.append("Maximum 2 subjects allowed")
        
        return len(self.errors) == 0
    
    def parse_names(self, full_name):
        """
        Split full name into first, middle (surname), and last names.
        Examples:
            "John Doe" -> first: John, surname: "", last: Doe
            "John Michael Doe" -> first: John, surname: Michael, last: Doe
            "John Michael Peter Doe" -> first: John, surname: Michael Peter, last: Doe
        """
        parts = full_name.strip().split()
        
        if len(parts) == 0:
            return "", "", ""
        elif len(parts) == 1:
            return parts[0], "", ""
        elif len(parts) == 2:
            return parts[0], "", parts[1]
        else:
            # First name, middle names as surname, last name
            first_name = parts[0]
            last_name = parts[-1]
            surname = " ".join(parts[1:-1])
            return first_name, surname, last_name
    
    
    def send_welcome_email(self, user, phone_number):
        """Send welcome email with login credentials."""
        try:
            subject = 'Welcome to TSCSwap - Your Account Has Been Created'
            
            context = {
                'user': user,
                'email': user.email,
                'password': phone_number,
                'login_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000',
            }
            
            # Render HTML email
            html_message = render_to_string('emails/welcome_email.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Welcome email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            # Don't fail the whole process if email fails
            return False
    
    @transaction.atomic
    def process(self):
        """
        Main processing function to create all required records.
        Uses transaction to ensure all-or-nothing creation.
        """
        if not self.validate():
            raise ValueError(f"Validation failed: {', '.join(self.errors)}")
        
        # Parse names
        full_name = self.form_data['full_name']
        first_name, surname, last_name = self.parse_names(full_name)
        
        # Get phone and email
        phone = self.form_data['phone']
        email = self.form_data['email'].lower().strip()
        
        # Get levels
        teacher_level_name = self.form_data['teacher_level']
        
        # Handle "Secondary/High School (JSS included)" mapping to DB "Secondary/High School"
        if "(JSS included)" in teacher_level_name:
            clean_level_name = teacher_level_name.replace(" (JSS included)", "").strip()
        else:
            clean_level_name = teacher_level_name
            
        try:
            teacher_level = Level.objects.get(name=clean_level_name)
        except Level.DoesNotExist:
            # Fallback/Error handling
            logger.error(f"Level not found: {clean_level_name} (Original: {teacher_level_name})")
            raise ValueError(f"Invalid teaching level: {teacher_level_name}")
        
        # Create User account with phone as password
        logger.info(f"Creating user account for {email}")
        user = User.objects.create_user(
            email=email,
            password=phone,  # Phone number as password
        )
        user.role = 'Teacher'
        user.is_active = True
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Create PersonalProfile (without school - user will add later)
        logger.info(f"Creating personal profile for {email}")
        profile = PersonalProfile.objects.create(
            user=user,
            first_name=first_name,
            surname=surname,
            last_name=last_name,
            phone=phone,
            level=teacher_level,  # Teacher's teaching level
            school=None,  # User will add school separately
            gender='O',  # Default, can be updated later
            location=None  # Will be set when school is added
        )
        
        # Create MySubject (only for secondary teachers)
        if "Secondary" in teacher_level_name:
            subjects = self.form_data.get('subjects', [])
            if subjects:
                logger.info(f"Creating subjects for {email}: {subjects}")
                my_subject = MySubject.objects.create(user=user)
                
                # Add subjects (expecting list of subject IDs)
                for subject_id in subjects:
                    subject = Subject.objects.get(id=subject_id)
                    my_subject.subject.add(subject)
                
                my_subject.save()
        
        # Create SwapPreference
        logger.info(f"Creating swap preferences for {email}")
        most_preferred_county = Counties.objects.get(id=self.form_data['most_preferred_county'])
        
        swap_pref = SwapPreference.objects.create(
            user=user,
            desired_county=most_preferred_county,
            desired_constituency=None,  # Not collected in form
            desired_ward=None,  # Not collected in form
            is_hardship='Any'  # Default, not collected in form
        )
        
        # Add all preferred counties to open_to_all
        preferred_counties = self.form_data.get('preferred_counties', [])
        for county_id in preferred_counties:
            county = Counties.objects.get(id=county_id)
            swap_pref.open_to_all.add(county)
        
        swap_pref.save()
        
        # Send welcome email
        self.send_welcome_email(user, phone)
        
        logger.info(f"Successfully created account for {email}")
        
        return {
            'success': True,
            'user_id': user.id,
            'email': user.email,
            'message': 'User account created successfully. Please add your school information after logging in.'
        }



def process_google_form_submission(form_data):
    """
    Main entry point for processing Google Form submissions.
    
    Args:
        form_data (dict): Dictionary containing form field values
        
    Returns:
        dict: Result dictionary with success status and message
    """
    try:
        processor = GoogleFormProcessor(form_data)
        result = processor.process()
        return result
        
    except Exception as e:
        logger.error(f"Error processing Google Form submission: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create user account'
        }
