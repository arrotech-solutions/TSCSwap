from home.fast_swap_utils import find_triangle_matches_for_fast_swap
from django.contrib.auth import get_user_model
import sys

# Force UTF-8 for print
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

User = get_user_model()
u7 = User.objects.filter(email='mock_user_7@example.com').first()
u8 = User.objects.filter(email='mock_user_8@example.com').first()

if not u7 or not u8:
    print("Mock users 7/8 not found!")
else:
    from home.models import FastSwap
    # Create a temp FastSwap for U7 to test the logic
    # U7 wants U8's county
    
    # Check if U7 matches criteria for FastSwap creation
    # For matching utils, it needs: level, subjects, most_preferred (or acceptable), current_county
    
    # Delete existing to be clean
    FastSwap.objects.filter(names=u7.get_full_name()).delete()
    
    fs = FastSwap.objects.create(
        names=u7.get_full_name(),
        phone=u7.profile.phone,
        level=u7.profile.level,
        most_preferred=u7.swappreference.desired_county,
        current_county=u7.profile.school.ward.constituency.county,
        school=u7.profile.school
    )
    # Add subjects
    fs.subjects.set(u7.mysubject_set.first().subject.all())
    
    print(f"Checking matches for FastSwap {fs} (Level: {fs.level}, Current: {fs.current_county}, Wants: {fs.most_preferred})...")
    
    # We must ensure u8 is a potential participant. 
    # Logic looks for OTHER users/fastswaps.
    
    results = find_triangle_matches_for_fast_swap(fs, fast_swap_only=False)
    print(f"Result Count: {len(results)}")
    
    for r in results:
        mf = r.get('missing_from')
        print(f"Type: {r['type']}")
        print(f"Missing From Value: {mf}")
        
        if mf is None:
            # Inspection
            b = r['entity_b']
            print(f"FAILED ENTITY B: {b['type']} ID={b['obj'].id}")
            targets = r.get('debug_targets', 'NOT CAPTURED IN RESULT') # Result doesn't have targets in dict, assume we can't see it easily unless we modify utils or re-derive
            # Re-derive targets for debug
            if b['type'] == 'fastswap':
                t = set([b['obj'].most_preferred.id] if b['obj'].most_preferred else [])
                t.update(b['obj'].acceptable_county.values_list('id', flat=True))
                print(f"Derive Targets: {t}")
            elif b['type'] == 'user':
                pref = b['obj'].swappreference
                t = set([pref.desired_county.id] if pref.desired_county else [])
                t.update(pref.open_to_all.values_list('id', flat=True))
                print(f"Derived Targets: {t}")
                if t:
                    from home.models import Counties
                    for tid in t:
                        c = Counties.objects.filter(id=tid).first()
                        print(f"Lookup County {tid}: {c}")

        if mf:
             print(f"Missing from Name: {getattr(mf, 'name', 'NO NAME ATTR')}")
        else:
             print("Missing From Value is STILL None!")
             
    # Clean up
    fs.delete()
