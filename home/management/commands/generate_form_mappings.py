"""
Django Management Command to Generate ID Mappings for Google Apps Script

This script generates JavaScript object mappings for subjects, counties,
constituencies, and wards to be used in the Google Apps Script.

Usage:
    python manage.py generate_form_mappings
"""

from django.core.management.base import BaseCommand
from home.models import Subject, Counties, Constituencies, Wards, Level


class Command(BaseCommand):
    help = 'Generate ID mappings for Google Apps Script'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Google Apps Script ID Mappings ===\n'))
        
        # Generate Subject Mapping
        self.stdout.write(self.style.WARNING('\n// Subject ID Mapping'))
        self.stdout.write('const subjectMap = {')
        
        try:
            secondary_level = Level.objects.get(name="Secondary/High School")
            subjects = Subject.objects.filter(level=secondary_level).order_by('name')
            
            for subject in subjects:
                # Escape single quotes in subject names
                name = subject.name.replace("'", "\\'")
                self.stdout.write(f"  '{name}': {subject.id},")
            
            self.stdout.write('};')
            self.stdout.write(self.style.SUCCESS(f'\n✓ Generated {subjects.count()} subject mappings'))
        except Level.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ Secondary/High School level not found in database'))
        
        # Generate County Mapping
        self.stdout.write(self.style.WARNING('\n\n// County ID Mapping'))
        self.stdout.write('const countyMap = {')
        
        counties = Counties.objects.all().order_by('name')
        for county in counties:
            name = county.name.replace("'", "\\'")
            self.stdout.write(f"  '{name}': {county.id},")
        
        self.stdout.write('};')
        self.stdout.write(self.style.SUCCESS(f'\n✓ Generated {counties.count()} county mappings'))
        
        # Generate Constituency Mapping
        self.stdout.write(self.style.WARNING('\n\n// Constituency ID Mapping'))
        self.stdout.write('const constituencyMap = {')
        
        constituencies = Constituencies.objects.all().order_by('name')
        for constituency in constituencies:
            name = constituency.name.replace("'", "\\'")
            self.stdout.write(f"  '{name}': {constituency.id},")
        
        self.stdout.write('};')
        self.stdout.write(self.style.SUCCESS(f'\n✓ Generated {constituencies.count()} constituency mappings'))
        
        # Generate Ward Mapping
        self.stdout.write(self.style.WARNING('\n\n// Ward ID Mapping'))
        self.stdout.write('const wardMap = {')
        
        wards = Wards.objects.all().order_by('name')
        for ward in wards:
            name = ward.name.replace("'", "\\'")
            self.stdout.write(f"  '{name}': {ward.id},")
        
        self.stdout.write('};')
        self.stdout.write(self.style.SUCCESS(f'\n✓ Generated {wards.count()} ward mappings'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n\n=== Summary ==='))
        self.stdout.write(f'Subjects: {subjects.count() if "subjects" in locals() else 0}')
        self.stdout.write(f'Counties: {counties.count()}')
        self.stdout.write(f'Constituencies: {constituencies.count()}')
        self.stdout.write(f'Wards: {wards.count()}')
        
        self.stdout.write(self.style.SUCCESS('\n\nCopy the above mappings and paste them into your Google Apps Script,'))
        self.stdout.write(self.style.SUCCESS('replacing the existing mapping objects.\n'))
