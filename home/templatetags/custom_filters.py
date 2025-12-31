from django import template
from home.models import MySubject

register = template.Library()

@register.filter(name='mask_phone')
def mask_phone(phone_number):
    if not phone_number:
        return ""
    
    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, str(phone_number)))
    
    # If the number is too short, return as is
    if len(digits) <= 4:
        return phone_number
    
    # Mask all but last 4 digits
    masked = '•' * (len(digits) - 4) + digits[-4:]
    
    # Format with spaces for better readability
    return ' '.join([masked[i:i+4] for i in range(0, len(masked), 4)])

@register.simple_tag
def get_total_subject_count(user):
    """Count total subjects across all MySubject objects for a user."""
    total = 0
    for mysubject in user.mysubject_set.all():
        total += mysubject.subject.count()
    return total
