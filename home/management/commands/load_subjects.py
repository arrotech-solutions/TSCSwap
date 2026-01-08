from django.core.management.base import BaseCommand
from home.models import Level, Subject

class Command(BaseCommand):
    help = 'Load subjects data into the database from a predefined dataset'
    
    def handle(self, *args, **options):
        # Dataset containing level names and their respective subjects
        # Format: {'Level Name': ['Subject1', 'Subject2', ...], ...}
        SUBJECTS_DATA = {
 

    'Secondary/High School': [
        # Compulsory
        'English',
        'Kiswahili',
        'Mathematics',

        # Sciences
        'Biology',
        'Chemistry',
        'Physics',

        # Humanities
        'History',
        'Geography',
        'CRE',
        'IRE',
        'HRE',

        # Languages
        'French',
        'German',
        'Arabic',

        # Applied / Technical
        'Business Studies',
        'Agriculture',
        'Computer Studies',
        'Home Science',
        'Art and Design',
        'Music',
        'Physical Education',
        'Aviation Technology',
        'Building Construction',
        'Electricity',
        'Power Mechanics',
        'Wood Technology',
        'Metal Technology',
        'Drawing and Design'
    ]
}

        
        created_count = 0
        
        for level_name, subjects in SUBJECTS_DATA.items():
            try:
                # Get or create the level
                level, created = Level.objects.get_or_create(
                    name=level_name,
                    defaults={
                        'code': level_name.upper()[:3]
                    }
                )
                
                # Create subjects for this level
                for subject_name in subjects:
                    subject, created = Subject.objects.get_or_create(
                        name=subject_name,
                        level=level,
                        defaults={
                            'code': ''.join(word[0].upper() for word in subject_name.split())
                        }
                    )
                    if created:
                        created_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'Successfully processed {level_name} level with {len(subjects)} subjects'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {level_name}: {str(e)}'))
        
        total_subjects = sum(len(subjects) for subjects in SUBJECTS_DATA.values())
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created/updated {created_count} out of {total_subjects} total subjects'))
