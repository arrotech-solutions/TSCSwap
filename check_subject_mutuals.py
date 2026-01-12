from django.contrib.auth import get_user_model
from home.models import Level, MySubject
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

User = get_user_model()

# Get secondary level
sec_level = Level.objects.filter(name__icontains='Secondary').first()
if not sec_level:
    print("No secondary level found")
    sys.exit(1)

print(f"Checking subject combinations with mutual swaps for: {sec_level.name}\n")

# Get all secondary users with swap preferences
sec_users = User.objects.filter(
    profile__level=sec_level,
    swappreference__isnull=False
).select_related(
    'profile__school__ward__constituency__county',
    'swappreference__desired_county'
).prefetch_related('swappreference__open_to_all', 'mysubject_set__subject')

# Group users by subject combination
subject_combos = {}
for user in sec_users:
    subjects = MySubject.objects.filter(user=user).prefetch_related('subject')
    if subjects.exists():
        subject_list = sorted([s.name for subj in subjects for s in subj.subject.all()])
        combo_key = " / ".join(subject_list)
        
        if combo_key not in subject_combos:
            subject_combos[combo_key] = []
        subject_combos[combo_key].append(user)

print(f"Found {len(subject_combos)} unique subject combinations\n")

# Check for mutual swaps within each combination
for combo, users in subject_combos.items():
    if len(users) < 2:
        continue
    
    mutual_found = False
    mutual_pairs = []
    
    for i, u1 in enumerate(users):
        if not u1.profile or not u1.profile.school or not u1.profile.school.ward:
            continue
        
        county1 = u1.profile.school.ward.constituency.county
        pref1 = u1.swappreference
        
        u1_wants = set()
        if pref1.desired_county:
            u1_wants.add(pref1.desired_county.id)
        u1_wants.update(pref1.open_to_all.values_list('id', flat=True))
        
        for j, u2 in enumerate(users):
            if i >= j:  # Avoid duplicates
                continue
            if not u2.profile or not u2.profile.school or not u2.profile.school.ward:
                continue
                
            county2 = u2.profile.school.ward.constituency.county
            pref2 = u2.swappreference
            
            u2_wants = set()
            if pref2.desired_county:
                u2_wants.add(pref2.desired_county.id)
            u2_wants.update(pref2.open_to_all.values_list('id', flat=True))
            
            # Check if mutual
            if county2.id in u1_wants and county1.id in u2_wants:
                mutual_found = True
                mutual_pairs.append((u1, county1, u2, county2))
    
    if mutual_found:
        print(f"=== {combo} ===")
        print(f"Total teachers: {len(users)}")
        print(f"Mutual swaps found: {len(mutual_pairs)}")
        for u1, c1, u2, c2 in mutual_pairs:
            print(f"  • {u1.email} ({c1.name}) ↔ {u2.email} ({c2.name})")
        print()
