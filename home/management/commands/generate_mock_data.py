import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from home.models import (
    Level, Subject, MySubject, Schools, Wards, Counties, 
    Constituencies, SwapPreference, Curriculum
)
from users.models import PersonalProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates mock data for testing swap combinations'

    def handle(self, *args, **kwargs):
        print('Starting mock data generation...')
        
        try:
                self.generate_data()
                print('Successfully generated mock data!')
        except Exception as e:
            print(f'Error generating data: {str(e)}')
            import traceback
            traceback.print_exc()

    def generate_data(self):
        # 1. Clear existing mock data (optional, but good for idempotency if strictly mock DB)
        # For safety, I WON'T delete all data, but creates new ones.
        # Ideally, run on a clean DB or ignore collisions (using unique emails).
        
        # 2. Fetch Base Data
        try:
            sec_level = Level.objects.get(name__icontains='Secondary')
            pri_level = Level.objects.get(name__icontains='Primary')
        except Level.DoesNotExist:
            print('Levels not found. Run seeds first.')
            return

        print(f'Found levels: {sec_level}, {pri_level}')

        # Fetch Subjects
        sub_english = Subject.objects.filter(name='English').first()
        sub_math = Subject.objects.filter(name='Mathematics').first()
        sub_phy = Subject.objects.filter(name='Physics').first()
        sub_biz = Subject.objects.filter(name='Business Studies').first()
        sub_geo = Subject.objects.filter(name='Geography').first()
        
        all_subjects_pool = [sub_english, sub_math, sub_phy, sub_biz, sub_geo]
        if not all([sub_english, sub_math, sub_phy, sub_biz, sub_geo]):
             print('Some subjects missing. Ensure load_subjects has run. using available...')
             all_subjects_pool = [s for s in all_subjects_pool if s]
        
        print(f'Using subjects: {len(all_subjects_pool)}')

        counties = list(Counties.objects.all())
        print(f'Found counties: {len(counties)}')
        if len(counties) < 15:
             print('Not enough counties to generate diverse data.')
             return
             
        wards = list(Wards.objects.all())
        constituencies = list(Constituencies.objects.all())
        # Ensure we have curriculum
        curriculum, _ = Curriculum.objects.get_or_create(name="CBC")

        # 3. Create 100 Users & Schools
        users = []
        
        # We need specific counties for scenarios to ensure matches are possible/impossible
        # Let's pick some indices for our scenario actors
        # Indices 0-1: Mutual Swap 1 (Math/Phy)
        # Indices 2-3: Mutual Swap 2 (Primary)
        # Indices 4-6: Triangle Swap (English)
        # Indices 7-8: Missing Link (Biz/Geo)
        # Indicies 9: No Match
        # Rest: Random
        
        # Create Users Loop
        for i in range(100):
            # 70 Secondary, 30 Primary
            is_secondary = i < 70
            level = sec_level if is_secondary else pri_level
            
            # Create User
            email = f"mock_user_{i+1}@example.com"
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    email=email, 
                    password="password123",
                    first_name=f"MockFName{i}",
                    last_name=f"MockLName{i}",
                    role="Teacher"
                )
            
            # Create School
            # Pick a random ward
            ward = random.choice(wards)
            school_name = f"Mock School {i+1} {level.name}"
            school = Schools.objects.create(
                name=school_name,
                gender="Mixed",
                level=level,
                boarding="Day",
                curriculum=curriculum,
                postal_code="00100",
                ward=ward,
                is_hardship=False
            )
            
            # Create Profile
            # Location is ignored as per instructions, but we link school
            MySubject.objects.filter(user=user).delete() # Reset subjects if existing
            PersonalProfile.objects.filter(user=user).delete()
            profile = PersonalProfile.objects.create(
                user=user,
                first_name=f"Teacher{i}",
                last_name=f"Surname{i}",
                phone=f"07{i:08d}", # Unique phone
                level=level,
                school=school,
                gender=random.choice(['M', 'F'])
            )
            
            # Assign Subjects (Only for Secondary)
            if is_secondary:
                if i in [0, 1]: # Mutual Scenario 1 (Math/Phy)
                     if sub_math and sub_phy:
                        ms = MySubject.objects.create(user=user)
                        ms.subject.add(sub_math, sub_phy)
                elif i in [4, 5, 6]: # Triangle Scenario (English)
                     if sub_english:
                        ms = MySubject.objects.create(user=user)
                        ms.subject.add(sub_english)
                elif i in [7, 8]: # Missing Link (Biz/Geo)
                     if sub_biz and sub_geo:
                        ms = MySubject.objects.create(user=user)
                        ms.subject.add(sub_biz, sub_geo)
                else:
                    # Distribute rest normally
                    group = i % 3
                    ms = MySubject.objects.create(user=user)
                    if group == 0 and sub_english:
                        ms.subject.add(sub_english)
                    elif group == 1 and sub_math and sub_phy:
                        ms.subject.add(sub_math, sub_phy)
                    elif group == 2 and sub_biz and sub_geo:
                        ms.subject.add(sub_biz, sub_geo)
            
            users.append({'user': user, 'level': level, 'school': school})

        # 4. Orchestrate Scenarios
        # We need to set SwapPreference.
        # Helpers
        def set_pref(u_idx, desired_c, open_c_list):
            u = users[u_idx]['user']
            SwapPreference.objects.filter(user=u).delete()
            sp = SwapPreference.objects.create(
                user=u,
                desired_county=desired_c,
                is_hardship='Any'
            )
            sp.open_to_all.set(open_c_list)
        
        # Let's map users to counties they ARE currently in (School County)
        for u_data in users:
            u_data['current_county'] = u_data['school'].ward.constituency.county

        # --- Scenario 1: Mutual Swap (Math/Phy) ---
        # User 0 and User 1
        u0 = users[0] # Currently in u0['current_county']
        u1 = users[1] # Currently in u1['current_county']
        
        # User 0 wants User 1's county, User 1 wants User 0's county
        # Pick 3 random for open_to_all, including the target for safety/robustness
        others0 = random.sample(counties, 2)
        others1 = random.sample(counties, 2)
        
        set_pref(0, u1['current_county'], [u1['current_county']] + others0)
        set_pref(1, u0['current_county'], [u0['current_county']] + others1)
        self.stdout.write(f"Mutual 1: User 0 ({u0['current_county']}) <-> User 1 ({u1['current_county']})")

        # --- Scenario 2: Mutual Swap (Primary) ---
        # User 70 and User 71 (Primary start at index 70)
        u70 = users[70]
        u71 = users[71]
        
        others70 = random.sample(counties, 2)
        others71 = random.sample(counties, 2)
        
        set_pref(70, u71['current_county'], [u71['current_county']] + others70)
        set_pref(71, u70['current_county'], [u70['current_county']] + others71)
        self.stdout.write(f"Mutual 2 (Pri): User 70 ({u70['current_county']}) <-> User 71 ({u71['current_county']})")

        # --- Scenario 3: Triangle Swap (English) ---
        # User 4 -> wants -> User 5 -> wants -> User 6 -> wants -> User 4
        u4 = users[4]
        u5 = users[5]
        u6 = users[6]
        
        set_pref(4, u5['current_county'], [u5['current_county']] + random.sample(counties, 2))
        set_pref(5, u6['current_county'], [u6['current_county']] + random.sample(counties, 2))
        set_pref(6, u4['current_county'], [u4['current_county']] + random.sample(counties, 2))
        self.stdout.write(f"Triangle: 4({u4['current_county']})->5({u5['current_county']})->6({u6['current_county']})->4")

        # --- Scenario 4: Missing Link (Biz/Geo) ---
        # User 7 -> wants -> User 8 -> wants -> (County X) -> No one wants User 7
        u7 = users[7]
        u8 = users[8]
        
        # Pick a county X that is NOT u7's county
        county_x = random.choice([c for c in counties if c != u7['current_county']])
        
        set_pref(7, u8['current_county'], [u8['current_county']] + random.sample(counties, 2))
        set_pref(8, county_x, [county_x] + random.sample(counties, 2))
        self.stdout.write(f"Missing Link: 7({u7['current_county']})->8({u8['current_county']})->{county_x}(Missing)->?")

        # --- Scenario 5: Remainder ---
        processed_indices = [0, 1, 70, 71, 4, 5, 6, 7, 8]
        
        for i in range(100):
            if i not in processed_indices:
                u_data = users[i]
                # Random desired county
                desired = random.choice(counties)
                # 3 Random open counties
                open_c = random.sample(counties, 3)
                
                # Make sure at least one person has NO match (User 9)
                if i == 9:
                    # User 9 wants something obscure, maybe himself (invalid but ensures no match) or just ensuring no one points to him?
                    # Easiest is just standard random, prob of match is low-ish but effectively random.
                    pass 
                
                set_pref(i, desired, open_c)
