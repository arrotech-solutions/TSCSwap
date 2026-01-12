from django.contrib.auth import get_user_model
from home.models import Level
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

print(f"Checking for secondary level: {sec_level.name}")

# Get all secondary users with swap preferences
sec_users = User.objects.filter(
    profile__level=sec_level,
    swappreference__isnull=False
).select_related(
    'profile__school__ward__constituency__county',
    'swappreference__desired_county'
).prefetch_related('swappreference__open_to_all')

print(f"\nTotal secondary users with preferences: {sec_users.count()}")

# Check for mutual swaps
print("\n=== CHECKING FOR MUTUAL SWAPS ===")
mutual_count = 0
for u1 in sec_users[:20]:  # Check first 20 to avoid timeout
    if not u1.profile or not u1.profile.school or not u1.profile.school.ward:
        continue
    
    county1 = u1.profile.school.ward.constituency.county
    pref1 = u1.swappreference
    
    # Get all counties u1 wants
    u1_wants = set()
    if pref1.desired_county:
        u1_wants.add(pref1.desired_county.id)
    u1_wants.update(pref1.open_to_all.values_list('id', flat=True))
    
    for u2 in sec_users:
        if u1.id == u2.id:
            continue
        if not u2.profile or not u2.profile.school or not u2.profile.school.ward:
            continue
            
        county2 = u2.profile.school.ward.constituency.county
        pref2 = u2.swappreference
        
        # Get all counties u2 wants
        u2_wants = set()
        if pref2.desired_county:
            u2_wants.add(pref2.desired_county.id)
        u2_wants.update(pref2.open_to_all.values_list('id', flat=True))
        
        # Check if mutual: u1 wants county2 AND u2 wants county1
        if county2.id in u1_wants and county1.id in u2_wants:
            mutual_count += 1
            print(f"MUTUAL: {u1.email} ({county1.name}) <-> {u2.email} ({county2.name})")
            if mutual_count >= 5:  # Limit output
                break
    
    if mutual_count >= 5:
        break

print(f"\nFound {mutual_count} mutual swaps (showing max 5)")

# Check for complete triangles
print("\n=== CHECKING FOR COMPLETE TRIANGLES ===")
triangle_count = 0
checked = 0
for u1 in sec_users[:15]:  # Limit to avoid timeout
    if not u1.profile or not u1.profile.school or not u1.profile.school.ward:
        continue
    
    county1 = u1.profile.school.ward.constituency.county
    pref1 = u1.swappreference
    
    u1_wants = set()
    if pref1.desired_county:
        u1_wants.add(pref1.desired_county.id)
    u1_wants.update(pref1.open_to_all.values_list('id', flat=True))
    
    for u2 in sec_users:
        if u1.id == u2.id:
            continue
        if not u2.profile or not u2.profile.school or not u2.profile.school.ward:
            continue
            
        county2 = u2.profile.school.ward.constituency.county
        
        # u1 wants county2?
        if county2.id not in u1_wants:
            continue
            
        pref2 = u2.swappreference
        u2_wants = set()
        if pref2.desired_county:
            u2_wants.add(pref2.desired_county.id)
        u2_wants.update(pref2.open_to_all.values_list('id', flat=True))
        
        # Find u3 where u2 wants county3 and u3 wants county1
        for u3 in sec_users:
            if u3.id in [u1.id, u2.id]:
                continue
            if not u3.profile or not u3.profile.school or not u3.profile.school.ward:
                continue
                
            county3 = u3.profile.school.ward.constituency.county
            
            # u2 wants county3?
            if county3.id not in u2_wants:
                continue
                
            pref3 = u3.swappreference
            u3_wants = set()
            if pref3.desired_county:
                u3_wants.add(pref3.desired_county.id)
            u3_wants.update(pref3.open_to_all.values_list('id', flat=True))
            
            # u3 wants county1? (complete triangle)
            if county1.id in u3_wants:
                triangle_count += 1
                print(f"TRIANGLE: {u1.email} ({county1.name}) -> {u2.email} ({county2.name}) -> {u3.email} ({county3.name}) -> back to {county1.name}")
                if triangle_count >= 3:
                    break
        
        if triangle_count >= 3:
            break
    
    checked += 1
    if triangle_count >= 3:
        break

print(f"\nFound {triangle_count} complete triangles (checked {checked} users, showing max 3)")
