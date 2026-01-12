import random
from django.db import transaction
from django.contrib.auth import get_user_model
from home.models import (
    Level, Subject, MySubject, Schools, Wards, Counties, 
    Constituencies, SwapPreference, Curriculum
)
from users.models import PersonalProfile
import sys

# Force UTF-8 for print
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

User = get_user_model()

# Override Email Backend to avoid timeouts
from django.conf import settings
settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

print('Starting mock data generation...')

# 1. Fetch Base Data
try:
    sec_levels = Level.objects.filter(name__icontains='Secondary')
    pri_levels = Level.objects.filter(name__icontains='Primary')
    if not sec_levels.exists() or not pri_levels.exists():
        print('Levels not found. Run seeds first.')
        # We can't return from top-level, so we use sys.exit or just skip
        sys.exit(1)
    sec_level = sec_levels.first()
    pri_level = pri_levels.first()
except Exception as e:
    print(f"Error fetching levels: {e}")
    sys.exit(1)

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

counties = list(Counties.objects.all())
print(f'Found counties: {len(counties)}')
if len(counties) < 15:
        print('Not enough counties to generate diverse data.')
        sys.exit(1)
        
wards = list(Wards.objects.all())
constituencies = list(Constituencies.objects.all())
curriculum, _ = Curriculum.objects.get_or_create(name="CBC")

# 3. Create 100 Users & Schools
users = []

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
    MySubject.objects.filter(user=user).delete() 
    PersonalProfile.objects.filter(user=user).delete()
    profile = PersonalProfile.objects.create(
        user=user,
        first_name=f"Teacher{i}",
        last_name=f"Surname{i}",
        phone=f"07{i:08d}",
        level=level,
        school=school,
        gender=random.choice(['M', 'F'])
    )
    
    # Assign Subjects (Only for Secondary)
    if is_secondary:
        if i in [0, 1]: 
                if sub_math and sub_phy:
                    ms = MySubject.objects.create(user=user)
                    ms.subject.add(sub_math, sub_phy)
        elif i in [4, 5, 6]:
                if sub_english:
                    ms = MySubject.objects.create(user=user)
                    ms.subject.add(sub_english)
        elif i in [7, 8]:
                if sub_biz and sub_geo:
                    ms = MySubject.objects.create(user=user)
                    ms.subject.add(sub_biz, sub_geo)
        else:
            group = i % 3
            ms = MySubject.objects.create(user=user)
            if group == 0 and sub_english:
                ms.subject.add(sub_english)
            elif group == 1 and sub_math and sub_phy:
                ms.subject.add(sub_math, sub_phy)
            elif group == 2 and sub_biz and sub_geo:
                ms.subject.add(sub_biz, sub_geo)
    
    users.append({'user': user, 'level': level, 'school': school})

print(f"Created {len(users)} users.")

# 4. Orchestrate Scenarios
def set_pref(u_idx, desired_c, open_c_list):
    u = users[u_idx]['user']
    SwapPreference.objects.filter(user=u).delete()
    sp = SwapPreference.objects.create(
        user=u,
        desired_county=desired_c,
        is_hardship='Any'
    )
    sp.open_to_all.set(open_c_list)

for u_data in users:
    u_data['current_county'] = u_data['school'].ward.constituency.county

# Mutual 1
if len(users) > 1:
    u0, u1 = users[0], users[1]
    others0, others1 = random.sample(counties, 2), random.sample(counties, 2)
    set_pref(0, u1['current_county'], [u1['current_county']] + others0)
    set_pref(1, u0['current_county'], [u0['current_county']] + others1)
    print(f"Mutual 1: {u0['current_county']} <-> {u1['current_county']}")

# Mutual 2
if len(users) > 71:
    u70, u71 = users[70], users[71]
    others70, others71 = random.sample(counties, 2), random.sample(counties, 2)
    set_pref(70, u71['current_county'], [u71['current_county']] + others70)
    set_pref(71, u70['current_county'], [u70['current_county']] + others71)
    print(f"Mutual 2: {u70['current_county']} <-> {u71['current_county']}")

# Triangle
if len(users) > 6:
    u4, u5, u6 = users[4], users[5], users[6]
    set_pref(4, u5['current_county'], [u5['current_county']] + random.sample(counties, 2))
    set_pref(5, u6['current_county'], [u6['current_county']] + random.sample(counties, 2))
    set_pref(6, u4['current_county'], [u4['current_county']] + random.sample(counties, 2))
    print(f"Triangle: {u4['current_county']}->{u5['current_county']}->{u6['current_county']}->{u4['current_county']}")

# Missing Link
if len(users) > 8:
    u7, u8 = users[7], users[8]
    county_x = random.choice([c for c in counties if c != u7['current_county']])
    set_pref(7, u8['current_county'], [u8['current_county']] + random.sample(counties, 2))
    set_pref(8, county_x, [county_x] + random.sample(counties, 2))
    print(f"Missing Link: {u7['current_county']}->{u8['current_county']}->{county_x}")

# Remainder
processed_indices = [0, 1, 70, 71, 4, 5, 6, 7, 8]
for i in range(100):
    if i < len(users) and i not in processed_indices:
        desired = random.choice(counties)
        open_c = random.sample(counties, 3)
        if i == 9: pass 
        set_pref(i, desired, open_c)

print('Successfully generated mock data with Flat Script!')
