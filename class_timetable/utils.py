import random
import itertools
from datetime import time, datetime, timedelta
from .models import (
    TycoAInput, TycoATimetable,
    TycoBInput, TycoBTimetable,
    SycoAInput, SycoATimetable,
    SycoBInput, SycoBTimetable,
    DAYS
)

# === CONFIGURATION ===
ACADEMIC_SLOTS = [
    (time(10, 0), time(11, 0)),
    (time(11, 0), time(12, 0)),
    (time(12, 45), time(13, 45)),
    (time(13, 45), time(14, 45)),
    (time(15, 0), time(16, 0)),
    (time(16, 0), time(17, 0)),
]

CLASS_CONFIG = {
    'tyco_a': {'input': TycoAInput, 'timetable': TycoATimetable, 'name': 'TYCO A'},
    'tyco_b': {'input': TycoBInput, 'timetable': TycoBTimetable, 'name': 'TYCO B'},
    'syco_a': {'input': SycoAInput, 'timetable': SycoATimetable, 'name': 'SYCO A'},
    'syco_b': {'input': SycoBInput, 'timetable': SycoBTimetable, 'name': 'SYCO B'},
}

# --- HELPER FOR ABBREVIATIONS ---
SUBJECT_ABBR = {
    "OPERATING SYSTEM": "OSY",
    "SOFTWARE ENGINEERING": "STE",
    "ENTREPRENEURSHIP DEVELOPMENT AND STARTUPS": "ENDS",
    "SEMINAR AND PROJECT INITIATION COURSE": "SPI",
    "CLOUD COMPUTING": "CLC",
    # SYCO A (Sem III)
    "Data Structure Using C": "DSU",
    "Database Management System": "DMS",
    "Digital Techniques": "DTE",
    "Object Oriented Programming Using C++": "OOP",
    "Computer Graphics": "CGR",
    "Essence Of Indian Constitution": "EIC",
    # SYCO A (Sem IV)
    "Environmental Education And Sustainability": "EES",
    "Java Programming": "JPR",
    "Data Communication And Computer Network": "DCN",
    "Microprocessor": "MIC",
    "Python Programming": "PWP",
    "User Interface Design": "UID"
}

def get_abbr(name):
    return SUBJECT_ABBR.get(name, name[:3].upper())

def check_teacher_conflict_bulk(teacher_list, day, start_time, exclude_class_key):
    """
    Returns True if ANY teacher in the list is busy in another class.
    """
    for key, cfg in CLASS_CONFIG.items():
        if key == exclude_class_key:
            continue
        
        # Check timetable of other class
        busy = cfg['timetable'].objects.filter(
            teacher_name__in=teacher_list, 
            day=day, 
            start_time=start_time
        ).exists()
        
        if busy:
            return True
    return False

def check_single_conflict(teacher, day, start_time, exclude_class_key):
    return check_teacher_conflict_bulk([teacher], day, start_time, exclude_class_key)

def generate_timetable_for_class(class_key):
    if class_key not in CLASS_CONFIG:
        return False, "Invalid Class"

    InputModel = CLASS_CONFIG[class_key]['input']
    TimetableModel = CLASS_CONFIG[class_key]['timetable']

    # 1. Clear Timetable
    TimetableModel.objects.all().delete()

    # 2. Fetch Inputs
    all_inputs = list(InputModel.objects.all())
    
    theory_pool = []
    
    for inp in all_inputs:
        # Theory
        for _ in range(inp.theory_credits):
            theory_pool.append(inp)
                
    random.shuffle(theory_pool)
    
    days_list = [d[0] for d in DAYS]
    grid = {} 
    
    # --- STEP A: SCHEDULE PRACTICALS ---
    lab_pools = {'A1': [], 'A2': [], 'A3': []}
    
    for inp in all_inputs:
        blocks = inp.practical_credits // 2
        for _ in range(blocks):
            for batch in ['A1', 'A2', 'A3']:
                lab_pools[batch].append(inp) # Add input object reference
                
    for b in lab_pools:
        random.shuffle(lab_pools[b])

    for day in days_list:
        possible_starts = [0, 2, 4]
        random.shuffle(possible_starts)
        
        placed_pr = False
        
        for start_slot in possible_starts:
            s1 = start_slot
            s2 = start_slot + 1
            if (day, s1) in grid or (day, s2) in grid:
                continue

            # Check pools
            if not lab_pools['A1'] or not lab_pools['A2'] or not lab_pools['A3']:
                break
                
            # Create all valid combinations from available pools using itertools
            p1 = lab_pools['A1']
            p2 = lab_pools['A2']
            p3 = lab_pools['A3']
            
            # Generate all combinations
            gen = itertools.product(p1, p2, p3)
            
            # To randomize, convert to list and shuffle (safe for small N)
            candidates = list(gen)
            random.shuffle(candidates)
            
            found_trio = None
            
            for tri_tuple in candidates:
                c1, c2, c3 = tri_tuple
                
                # 1. Unique Teachers Check
                teachers = {c1.teacher_name, c2.teacher_name, c3.teacher_name}
                if len(teachers) < 3:
                    continue
                    
                # 2. Conflict Check (External Timetables)
                if check_teacher_conflict_bulk(list(teachers), day, ACADEMIC_SLOTS[s1][0], class_key): continue
                if check_teacher_conflict_bulk(list(teachers), day, ACADEMIC_SLOTS[s2][0], class_key): continue
                
                # Found valid!
                found_trio = [c1, c2, c3]
                break
            
            if found_trio:
                # Place
                grid[(day, s1)] = {'type': 'PR', 'trio': found_trio, 'batches': ['A1', 'A2', 'A3']}
                grid[(day, s2)] = {'type': 'PR', 'trio': found_trio, 'batches': ['A1', 'A2', 'A3']}
                
                # Remove from pools
                lab_pools['A1'].remove(found_trio[0])
                lab_pools['A2'].remove(found_trio[1])
                lab_pools['A3'].remove(found_trio[2])
                
                placed_pr = True
                break
        
        # Limit 1 PR block per day? No, allow multiple if needed (e.g. Morning & Afternoon)
        # if placed_pr:
        #     continue 
    
    # --- STEP A.5: BACKFILL PRACTICAL WORKLOAD (DEFICIT) BEFORE THEORY ---
    # This ensures any low-load batches get filled in empty slots even if not full trios.
    
    # 1. Calculate deficit
    practical_deficit = {} 
    
    # We must scan current grid to see what was placed in Step A
    for inp in all_inputs:
        if inp.practical_credits > 0:
            expected_blocks = inp.practical_credits // 2
            for batch in ['A1', 'A2', 'A3']:
                actual_count = 0
                for (day, slot_idx), data in grid.items():
                    if data.get('type') == 'PR':
                        trio = data.get('trio', [])
                        batches = data.get('batches', [])
                        for idx, b in enumerate(batches):
                            if b == batch and idx < len(trio) and trio[idx].id == inp.id:
                                actual_count += 1
                                break
                actual_blocks = actual_count // 2
                if actual_blocks < expected_blocks:
                    deficit = expected_blocks - actual_blocks
                    practical_deficit[(inp.id, batch)] = {'subject': inp, 'deficit': deficit}
                    
    if practical_deficit:
        # Find empty 2-hour blocks
        empty_blocks = []
        for day in days_list:
            for start_slot in [0, 2, 4]:
                s1, s2 = start_slot, start_slot + 1
                if (day, s1) not in grid and (day, s2) not in grid:
                    empty_blocks.append((day, start_slot))
        
        random.shuffle(empty_blocks)
        
        class DummyLab:
             subject_name = "Library"
             teacher_name = "-"
             id = -1

        for day, start_slot in empty_blocks:
            if not practical_deficit: break
            s1, s2 = start_slot, start_slot + 1
            
            # Group candidates
            batch_candidates = {'A1': [], 'A2': [], 'A3': []}
            for key, data in practical_deficit.items():
                batch_candidates[data['subject'].id, key[1]] = data['subject'] # Avoid duplicates? No, keys distinct
                batch_candidates[key[1]].append(data['subject'])

            def is_valid_combo(combo_items):
                real_items = [x for x in combo_items if x is not None]
                if not real_items: return False
                teachers = set()
                for item in real_items:
                    if item.teacher_name in teachers: return False
                    teachers.add(item.teacher_name)
                t_list = list(teachers)
                if check_teacher_conflict_bulk(t_list, day, ACADEMIC_SLOTS[s1][0], class_key): return False
                if check_teacher_conflict_bulk(t_list, day, ACADEMIC_SLOTS[s2][0], class_key): return False
                return True

            final_combo = None
            
            # 1. Full Trio
            if batch_candidates['A1'] and batch_candidates['A2'] and batch_candidates['A3']:
                # Limited attempts for performance
                prod_iter = itertools.product(batch_candidates['A1'], batch_candidates['A2'], batch_candidates['A3'])
                # Convert first 50 to list to shuffle? Or just iterate?
                # If lists are small, list(all) is fine.
                try: 
                    # If lists are huge, list() might hang. But lab candidates are few.
                    cands = list(prod_iter)
                    random.shuffle(cands)
                    for c in cands:
                        if is_valid_combo(c):
                            final_combo = c
                            break
                except: pass

            # 2. Pair
            if not final_combo:
                 l1 = batch_candidates['A1'] + [None]
                 l2 = batch_candidates['A2'] + [None]
                 l3 = batch_candidates['A3'] + [None]
                 
                 # Random probing
                 for _ in range(50):
                     c1 = random.choice(l1)
                     c2 = random.choice(l2)
                     c3 = random.choice(l3)
                     if c1 is None and c2 is None and c3 is None: continue
                     # Ensure we have at least TWO real items for Pair priority
                     real = [x for x in [c1,c2,c3] if x]
                     if len(real) < 2: continue
                     
                     if is_valid_combo((c1, c2, c3)):
                         final_combo = (c1, c2, c3)
                         break

            # 3. Single
            if not final_combo:
                 # Explicit iterate over all single candidates
                 singles = []
                 for x in batch_candidates['A1']: singles.append((x, None, None))
                 for x in batch_candidates['A2']: singles.append((None, x, None))
                 for x in batch_candidates['A3']: singles.append((None, None, x))
                 random.shuffle(singles)
                 for c in singles:
                     if is_valid_combo(c):
                         final_combo = c
                         break

            if final_combo:
                safe_trio = [x if x else DummyLab() for x in final_combo]
                grid[(day, s1)] = {'type': 'PR', 'trio': safe_trio, 'batches': ['A1', 'A2', 'A3']}
                grid[(day, s2)] = {'type': 'PR', 'trio': safe_trio, 'batches': ['A1', 'A2', 'A3']}
                
                for idx, batch in enumerate(['A1', 'A2', 'A3']):
                    subj = safe_trio[idx]
                    if subj.id != -1:
                        key = (subj.id, batch)
                        if key in practical_deficit:
                            practical_deficit[key]['deficit'] -= 1
                            if practical_deficit[key]['deficit'] <= 0:
                                del practical_deficit[key]
            
    # --- STEP B: SCHEDULE THEORY ---
    subject_daily_counts = {} 
    
    for day in days_list:
        available_slots = [i for i in range(len(ACADEMIC_SLOTS)) if (day, i) not in grid]
        random.shuffle(available_slots)
        
        for slot_idx in available_slots:
            if not theory_pool: break
            
            placed_t = None
            
            candidates_indices = list(range(len(theory_pool)))
            random.shuffle(candidates_indices)
            
            for i in candidates_indices:
                candidate = theory_pool[i]
                start_time = ACADEMIC_SLOTS[slot_idx][0]
                
                # 1. Conflict Check
                if check_single_conflict(candidate.teacher_name, day, start_time, class_key):
                    continue
                    
                # 2. Daily Limit Check (Max 2 per day)
                s_key = (day, candidate.id)
                current_count = subject_daily_counts.get(s_key, 0)
                if current_count >= 2:
                    continue
                
                # Found valid
                placed_t = candidate
                theory_pool.pop(i) # Remove from pool
                
                subject_daily_counts[s_key] = current_count + 1
                break
            
            if placed_t:
                grid[(day, slot_idx)] = {'type': 'TH', 'subject': placed_t, 'batch': 'ALL'}
                
    # --- STEP C: BACKFILL UNSCHEDULED WORKLOAD (REQUIRED) ---
    # 1. Try to place remaining theory items into empty slots
    if theory_pool:
        empty_slots = []
        for d in days_list:
            for s in range(len(ACADEMIC_SLOTS)):
                if (d, s) not in grid:
                    empty_slots.append((d, s))
        
        random.shuffle(empty_slots)
        
        for d, s in empty_slots:
            if not theory_pool:
                break
            
            start_time = ACADEMIC_SLOTS[s][0]
            placed_idx = -1
            
            for i, cand in enumerate(theory_pool):
                if not check_single_conflict(cand.teacher_name, d, start_time, class_key):
                    grid[(d, s)] = {'type': 'TH', 'subject': cand, 'batch': 'ALL'}
                    placed_idx = i
                    break
            
            if placed_idx != -1:
                theory_pool.pop(placed_idx)





    # --- STEP D: FILL REMAINING GAPS WITH EXTRA LECTURES ---
    # User Request: "extra lecture should be 1 dont add library lecture"
    # Logic: Fill empty slots with subjects, prioritizing those with low extra count.
    
    # 1. Identify remaining empty slots
    final_gaps = []
    for day in days_list:
        for i in range(len(ACADEMIC_SLOTS)):
            if (day, i) not in grid:
                final_gaps.append((day, i))
    
    if final_gaps:
        # Create a pool of candidates for extra lectures
        # We want to distribute extras evenly.
        unique_subjects = list(all_inputs)
        extra_counts = {s.id: 0 for s in unique_subjects}
        
        # Sort gaps randomly to distribute across week
        random.shuffle(final_gaps)
        
        for day, slot_idx in final_gaps:
            # Check if Step B or Backfill Theory already filled this?
            # grid was checked before loop using 'if (day, i) not in grid'.
            # But grid is not modified inside the loop unless we place something.
            # So double check
            if (day, slot_idx) in grid: continue

            start_time = ACADEMIC_SLOTS[slot_idx][0]
            
            # Find best candidate: Lowest extra count first
            # Sort candidates by extra_counts[id] ASC
            candidates = sorted(unique_subjects, key=lambda s: extra_counts[s.id])
            
            placed_extra = None
            for cand in candidates:
                # Limit: Try to keep extras <= 1 per subject if possible
                
                # Check Conflict
                if not check_single_conflict(cand.teacher_name, day, start_time, class_key):
                    placed_extra = cand
                    break
            
            if placed_extra:
                grid[(day, slot_idx)] = {'type': 'EXTRA', 'subject': placed_extra, 'batch': 'ALL'}
                extra_counts[placed_extra.id] += 1
            else:
                # If absolutely no teacher is free (rare), we must leave it or mark Library
                grid[(day, slot_idx)] = {'type': 'FILLER', 'subject_name': 'Library', 'batch': 'ALL'}
    for item in grid.items():
        key, data = item
        day, slot_idx = key
        start, end = ACADEMIC_SLOTS[slot_idx]
        
        if data['type'] in ['TH', 'EXTRA']:
            subj = data.get('subject')
            
            # Use abbreviation
            base_name = get_abbr(subj.subject_name)
            
            if data['type'] == 'EXTRA':
                s_name = f"{base_name} - E"
            else:
                s_name = base_name

            t_name = subj.teacher_name
            
            TimetableModel.objects.create(
                day=day, start_time=start, end_time=end,
                subject_name=s_name, teacher_name=t_name, batch='ALL'
            )

        elif data['type'] == 'PR':
            trio_labs = data['trio']
            for idx, batch_code in enumerate(['A1', 'A2', 'A3']):
                if idx < len(trio_labs):
                    lab_obj = trio_labs[idx]
                    s_name = get_abbr(lab_obj.subject_name)
                    t_name = lab_obj.teacher_name
                else:
                    s_name = "Free"
                    t_name = "-"
                
                TimetableModel.objects.create(
                    day=day, start_time=start, end_time=end,
                    subject_name=s_name, teacher_name=t_name, batch=batch_code
                )
        
        elif data['type'] == 'FILLER':
            TimetableModel.objects.create(
                day=day, start_time=start, end_time=end,
                subject_name="Library", teacher_name="-", batch='ALL'
            )

    return True, "Generated"

def validate_workload_distribution(class_key):
    """
    Comprehensive validation of practical and theory workload distribution.
    Returns detailed report on what's missing and what needs to be redistributed.
    """
    if class_key not in CLASS_CONFIG:
        return {'error': 'Invalid Class'}
    
    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg['timetable']
    InputModel = cfg['input']
    
    validation = {
        'theory_distribution': [],
        'practical_distribution': [],
        'theory_balanced': True,
        'practical_balanced': True,
        'total_theory_deficit': 0,
        'total_practical_deficit': 0,
        'recommendations': []
    }
    
    inputs = InputModel.objects.all()
    
    for inp in inputs:
        # === THEORY VALIDATION ===
        exp_theory = inp.theory_credits
        abbr = get_abbr(inp.subject_name)
        
        # Count actual theory sessions (excluding extras)
        actual_theory = TimetableModel.objects.filter(
            subject_name=abbr,
            batch='ALL'
        ).exclude(subject_name__contains=' - E').count()
        
        # Count extra sessions
        extra_theory = TimetableModel.objects.filter(
            subject_name__contains=f"{abbr} - E",
            batch='ALL'
        ).count()
        
        theory_status = "OK"
        if actual_theory < exp_theory:
            deficit = exp_theory - actual_theory
            theory_status = f"DEFICIT: {deficit} sessions"
            validation['theory_balanced'] = False
            validation['total_theory_deficit'] += deficit
            validation['recommendations'].append(
                f"Add {deficit} more theory session(s) for {inp.subject_name}"
            )
        elif actual_theory > exp_theory:
            excess = actual_theory - exp_theory
            theory_status = f"EXCESS: {excess} sessions"
        
        validation['theory_distribution'].append({
            'subject': inp.subject_name,
            'teacher': inp.teacher_name,
            'expected': exp_theory,
            'actual': actual_theory,
            'extra': extra_theory,
            'status': theory_status
        })
        
        # === PRACTICAL VALIDATION (PER BATCH) ===
        if inp.practical_credits > 0:
            exp_practical_blocks = inp.practical_credits // 2
            
            for batch in ['A1', 'A2', 'A3']:
                # Count practical sessions for this batch
                # Each practical block appears in 2 consecutive slots
                practical_entries = TimetableModel.objects.filter(
                    subject_name=abbr,
                    batch=batch
                ).order_by('day', 'start_time')
                
                # Count unique blocks (consecutive pairs)
                actual_blocks = 0
                prev_entry = None
                for entry in practical_entries:
                    if prev_entry:
                        # Check if this is consecutive with previous
                        time_diff = (datetime.combine(datetime.today(), entry.start_time) - 
                                   datetime.combine(datetime.today(), prev_entry.end_time)).seconds
                        if time_diff <= 900:  # Within 15 minutes (accounting for breaks)
                            actual_blocks += 1
                            prev_entry = None
                            continue
                    prev_entry = entry
                
                # If odd number of entries, count the last one as a partial block
                if len(practical_entries) % 2 == 1:
                    actual_blocks += 0.5
                
                practical_status = "OK"
                if actual_blocks < exp_practical_blocks:
                    deficit = exp_practical_blocks - actual_blocks
                    practical_status = f"DEFICIT: {deficit} blocks"
                    validation['practical_balanced'] = False
                    validation['total_practical_deficit'] += deficit
                    validation['recommendations'].append(
                        f"Add {deficit} practical block(s) for {inp.subject_name} - Batch {batch}"
                    )
                elif actual_blocks > exp_practical_blocks:
                    excess = actual_blocks - exp_practical_blocks
                    practical_status = f"EXCESS: {excess} blocks"
                
                validation['practical_distribution'].append({
                    'subject': inp.subject_name,
                    'teacher': inp.teacher_name,
                    'batch': batch,
                    'expected_blocks': exp_practical_blocks,
                    'actual_blocks': actual_blocks,
                    'status': practical_status
                })
    
    # Overall assessment
    if validation['theory_balanced'] and validation['practical_balanced']:
        validation['overall_status'] = "BALANCED"
    elif not validation['theory_balanced'] and not validation['practical_balanced']:
        validation['overall_status'] = "CRITICAL: Both theory and practical workload unbalanced"
    elif not validation['theory_balanced']:
        validation['overall_status'] = "WARNING: Theory workload unbalanced"
    else:
        validation['overall_status'] = "WARNING: Practical workload unbalanced"
    
    return validation

def analyze_timetable(class_key):
    """
    Analyzes the generated timetable for conflicts and workload distribution.
    """
    if class_key not in CLASS_CONFIG:
        return {'error': 'Invalid Class'}
        
    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg['timetable']
    InputModel = cfg['input']
    
    analysis = {
        'conflicts': [],
        'distribution': [],
        'is_balanced': True,
        'has_conflicts': False
    }
    
    # 1. Check Conflicts
    my_entries = TimetableModel.objects.all()
    
    for entry in my_entries:
        if entry.teacher_name in ['-', 'Free']:
            continue
            
        # Check against all other classes
        for other_key, other_cfg in CLASS_CONFIG.items():
            if other_key == class_key:
                continue
            
            OtherTimetable = other_cfg['timetable']
            
            overlaps = OtherTimetable.objects.filter(
                teacher_name=entry.teacher_name,
                day=entry.day,
                start_time=entry.start_time
            )
            
            for overlap in overlaps:
                analysis['conflicts'].append({
                    'teacher': entry.teacher_name,
                    'day': entry.day,
                    'time': f"{entry.start_time} - {entry.end_time}",
                    'other_class': other_cfg['name'],
                    'other_subject': overlap.subject_name
                })
                analysis['has_conflicts'] = True

    # 2. Check Workload Distribution
    inputs = InputModel.objects.all()
    
    for inp in inputs:
        exp_th = inp.theory_credits
        exp_pr = inp.practical_credits # Total practical hours (credits)
        
        abbr = get_abbr(inp.subject_name)
        
        act_th = TimetableModel.objects.filter(
            subject_name__startswith=abbr, 
            batch='ALL'
        ).count()
        
        # ACT PR: Sum of entries across all batches
        act_pr = TimetableModel.objects.filter(
            subject_name=abbr,
            batch__in=['A1', 'A2', 'A3']
        ).count()
        
        status = "Balanced"
        if act_th < exp_th:
            status = "Underloaded (Theory)"
            analysis['is_balanced'] = False
        elif act_th > (exp_th + 2): 
            status = "Overloaded (Theory)"
        
        # Check Practical Batch-wise
        batches = ['A1', 'A2', 'A3']
        pr_status = []
        for b in batches:
            b_act = TimetableModel.objects.filter(subject_name=abbr, batch=b).count()
            if b_act < exp_pr:
                pr_status.append(f"{b}: Low ({b_act}/{exp_pr})")
                analysis['is_balanced'] = False
            elif b_act > exp_pr:
                 pr_status.append(f"{b}: High ({b_act}/{exp_pr})")
        
        analysis['distribution'].append({
            'subject': inp.subject_name,
            'teacher': inp.teacher_name,
            'expected_th': exp_th,
            'actual_th': act_th,
            'expected_pr': exp_pr,
            'practical_status': ", ".join(pr_status) if pr_status else "OK",
            'status': status
        })

    return analysis
