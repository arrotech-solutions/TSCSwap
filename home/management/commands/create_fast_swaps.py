from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import MyUser, PersonalProfile
from home.models import FastSwap, MySubject, SwapPreference, Schools

class Command(BaseCommand):
    help = 'Populates FastSwap entries from user profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing FastSwap entries if phone matches',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing FastSwap entries before syncing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing all existing FastSwap entries...'))
            FastSwap.objects.all().delete()

        users = MyUser.objects.filter(profile__isnull=False).select_related('profile')
        count = 0
        updated_count = 0

        for user in users:
            profile = user.profile
            if not profile.phone:
                self.stdout.write(self.style.NOTICE(f"Skipping user {user.email}: No phone number"))
                continue

            # Subjects
            user_subjects_obj = MySubject.objects.filter(user=user).first()
            if not user_subjects_obj:
                self.stdout.write(self.style.NOTICE(f"Skipping user {user.email}: No subjects defined"))
                continue
            
            subjects = list(user_subjects_obj.subject.all())
            if not subjects:
                 self.stdout.write(self.style.NOTICE(f"Skipping user {user.email}: No subjects assigned"))
                 continue

            # Preferences
            pref = SwapPreference.objects.filter(user=user).first()
            most_preferred = pref.desired_county if pref else None
            acceptable_counties = list(pref.open_to_all.all()) if pref else []

            # Name construction
            name_parts = [profile.first_name, profile.surname, profile.last_name]
            full_name = " ".join([p for p in name_parts if p]).strip()
            if not full_name:
                full_name = user.email

            # School-based location
            current_county = None
            current_constituency = None
            current_ward = None
            
            if profile.school:
                current_ward = profile.school.ward
                if current_ward:
                    current_constituency = current_ward.constituency
                    if current_constituency:
                        current_county = current_constituency.county

            # Create or update
            defaults = {
                'names': full_name,
                'school': profile.school,
                'level': profile.level,
                'current_county': current_county,
                'current_constituency': current_constituency,
                'current_ward': current_ward,
                'most_preferred': most_preferred,
            }

            if not profile.level:
                self.stdout.write(self.style.WARNING(f"Warning: User {user.email} has no level. FastSwap requires level."))
                # We'll skip if no level to avoid IntegrityError if level is required
                continue

            with transaction.atomic():
                fast_swap, created = FastSwap.objects.get_or_create(
                    phone=profile.phone,
                    defaults=defaults
                )

                if not created and options['update']:
                    for key, value in defaults.items():
                        setattr(fast_swap, key, value)
                    fast_swap.save()
                    updated_count += 1
                
                if created or options['update']:
                    # Set ManyToMany relationships
                    fast_swap.subjects.set(subjects)
                    fast_swap.acceptable_county.set(acceptable_counties)
                    if created:
                        count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} FastSwap entries.'))
        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} existing FastSwap entries.'))
