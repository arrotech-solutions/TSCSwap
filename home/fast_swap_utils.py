from django.db.models import Q
from users.models import MyUser
from home.models import FastSwap, MySubject

def get_fast_swap_current_county(fs):
    return fs.current_county

def get_user_current_county(user):
    if hasattr(user, 'profile') and user.profile and user.profile.school and user.profile.school.ward:
        try:
            return user.profile.school.ward.constituency.county
        except:
            return None
    return None

def fs_wants_county(fs, county):
    if not county:
        return False
    if fs.most_preferred and fs.most_preferred.id == county.id:
        return True
    if fs.acceptable_county.filter(id=county.id).exists():
        return True
    return False

def user_wants_county(user, county):
    if not county or not hasattr(user, 'swappreference'):
        return False
    pref = user.swappreference
    if pref.desired_county and pref.desired_county.id == county.id:
        return True
    if pref.open_to_all.filter(id=county.id).exists():
        return True
    return False

def get_fs_subjects(fs):
    return set(fs.subjects.values_list('id', flat=True))

def get_user_subjects(user):
    return set(MySubject.objects.filter(user=user).values_list('subject__id', flat=True))

def find_mutual_matches_for_fast_swap(fs):
    """
    Finds mutual matches for a FastSwap instance.
    Returns:
        {
            'fast_swaps': list of matching FastSwap objects,
            'users': list of matching MyUser objects
        }
    """
    fs_level = fs.level
    fs_county = fs.current_county
    is_secondary = 'secondary' in fs_level.name.lower() or 'high' in fs_level.name.lower()
    fs_subjects = get_fs_subjects(fs) if is_secondary else set()

    # 1. Match with other FastSwaps
    # They want MY county AND I want THEIR county
    # Filter by level and active (FastSwap doesn't have active field, assume all are active)
    fs_target_counties = [fs.most_preferred.id] if fs.most_preferred else []
    fs_target_counties.extend(list(fs.acceptable_county.values_list('id', flat=True)))
    
    if not fs_target_counties:
        matching_fs = FastSwap.objects.none()
    else:
        # Conditions for other FastSwap (ofs):
        # 1. ofs level matches fs level
        # 2. ofs current_county in fs_target_counties
        # 3. ofs wants fs_county
        matching_fs = FastSwap.objects.filter(
            ~Q(id=fs.id),
            level=fs_level,
            current_county__id__in=fs_target_counties
        ).filter(
            Q(most_preferred=fs_county) | Q(acceptable_county=fs_county)
        ).distinct()

        if is_secondary:
            valid_ids = []
            for ofs in matching_fs:
                if get_fs_subjects(ofs) == fs_subjects:
                    valid_ids.append(ofs.id)
            matching_fs = matching_fs.filter(id__in=valid_ids)

    # 2. Match with MyUsers
    matching_users = MyUser.objects.filter(
        is_active=True,
        profile__level=fs_level,
        profile__school__ward__constituency__county__id__in=fs_target_counties
    ).filter(
        Q(swappreference__desired_county=fs_county) | Q(swappreference__open_to_all=fs_county)
    ).select_related(
        'profile__school__ward__constituency__county',
        'swappreference__desired_county'
    ).distinct()

    if is_secondary:
        valid_user_ids = []
        if not fs_subjects: #fs has no subjects
             matching_users = MyUser.objects.none()
        else:
            for user in matching_users:
                if get_user_subjects(user) == fs_subjects:
                    valid_user_ids.append(user.id)
            matching_users = matching_users.filter(id__in=valid_user_ids)

    return {
        'fast_swaps': list(matching_fs),
        'users': list(matching_users)
    }

def find_triangle_matches_for_fast_swap(fs, fast_swap_only=True, level_strict=True):
    """
    Finds triangle and mutual matches for a FastSwap instance.
    - Mutual: A <-> B
    - Triangle: A -> B -> C -> A
    - Incomplete: A -> B -> (missing C) or A -> B -> C (C doesn't want A)
    """
    fs_level = fs.level
    fs_county = fs.current_county
    if not fs_county or not fs_level:
        return []
        
    is_secondary = 'secondary' in fs_level.name.lower() or 'high' in fs_level.name.lower()
    fs_subjects = get_fs_subjects(fs) if is_secondary else set()

    # Participants pool
    potential_participants = []
    
    # FastSwaps
    p_fs_queryset = FastSwap.objects.filter(
        current_county__isnull=False
    ).exclude(id=fs.id).prefetch_related('acceptable_county', 'subjects')
    
    if level_strict:
        p_fs_queryset = p_fs_queryset.filter(level=fs_level)
    
    for ofs in p_fs_queryset:
        if not is_secondary or get_fs_subjects(ofs) == fs_subjects:
            targets = set([ofs.most_preferred.id] if ofs.most_preferred else [])
            targets.update(ofs.acceptable_county.values_list('id', flat=True))
            potential_participants.append({
                'type': 'fastswap',
                'obj': ofs,
                'county': ofs.current_county,
                'targets': targets
            })

    # Users
    if not fast_swap_only:
        p_u_queryset = MyUser.objects.filter(
            is_active=True,
            profile__school__ward__constituency__county__isnull=False,
            swappreference__isnull=False
        ).select_related(
            'profile__school__ward__constituency__county',
            'swappreference__desired_county'
        ).prefetch_related('swappreference__open_to_all')
        
        if level_strict:
            p_u_queryset = p_u_queryset.filter(profile__level=fs_level)
            
        for u in p_u_queryset:
            if not is_secondary or get_user_subjects(u) == fs_subjects:
                u_county = get_user_current_county(u)
                if u_county:
                    targets = set([u.swappreference.desired_county.id] if u.swappreference.desired_county else [])
                    targets.update(u.swappreference.open_to_all.values_list('id', flat=True))
                    potential_participants.append({
                        'type': 'user',
                        'obj': u,
                        'county': u_county,
                        'targets': targets
                    })

    # A's targets
    fs_targets = set([fs.most_preferred.id] if fs.most_preferred else [])
    fs_targets.update(fs.acceptable_county.values_list('id', flat=True))

    results = []
    processed_keys = set()

    # 1. Find B that A wants
    for b in potential_participants:
        if b['county'].id not in fs_targets:
            continue
            
        # Is it a Mutual Swap? (A -> B, B -> A)
        if fs_county.id in b['targets']:
            key = tuple(sorted([f"fs_{fs.id}", f"{b['type']}_{b['obj'].id}"]))
            if key not in processed_keys:
                processed_keys.add(key)
                results.append({
                    'type': 'mutual',
                    'entity_b': {'type': b['type'], 'obj': b['obj']},
                    'is_complete': True
                })
            continue # If mutual, we don't necessarily need to show it as a triangle too

        # 2. Look for C for A -> B -> C
        found_c = False
        for c in potential_participants:
            if c['obj'].id == b['obj'].id and c['type'] == b['type']:
                continue
                
            if c['county'].id in b['targets']:
                # Chain A -> B -> C exists
                # Is it a complete triangle? (C -> A)
                is_complete = fs_county.id in c['targets']
                
                key = (tuple(sorted([f"fs_{fs.id}", f"{b['type']}_{b['obj'].id}", f"{c['type']}_{c['obj'].id}"])), is_complete)
                if key not in processed_keys:
                    processed_keys.add(key)
                    results.append({
                        'type': 'triangle',
                        'entity_b': {'type': b['type'], 'obj': b['obj']},
                        'entity_c': {'type': c['type'], 'obj': c['obj']},
                        'is_complete': is_complete,
                        'missing_from': c['county'] if not is_complete else None,
                        'missing_to': fs_county if not is_complete else None
                    })
                    found_c = True
                    # We continue to find MORE Cs for this B, up to a reasonable limit?
                    # For now, let's allow finding multiple Cs.
        
        # 3. If no C found in DB, show A -> B -> (Missing C)
        if not found_c:
            # For each target of B, if no participant exists there, show one "Missing Link"
            # To avoid clutter, just show one "Missing Link" representing B's preferences
            if b['targets']:
                results.append({
                    'type': 'triangle',
                    'entity_b': {'type': b['type'], 'obj': b['obj']},
                    'entity_c': None,
                    'is_complete': False,
                    # Pick the first target as the representative "Missing" one, or show a summary
                    'missing_from': b['obj'].most_preferred if b['type'] == 'fastswap' and b['obj'].most_preferred else None,
                    'missing_to': fs_county
                })

    return results

    return triangles
