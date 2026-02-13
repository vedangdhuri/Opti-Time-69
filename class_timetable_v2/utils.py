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
# Based on User Images:
# 10:00 - 11:00
# 11:00 - 12:00
# 12:00 - 12:45 (LUNCH)
# 12:45 - 01:45
# 01:45 - 02:45
# 02:45 - 03:00 (TEA)
# 03:00 - 04:00
# 04:00 - 05:00

# We only define SCHEDULABLE slots here for the algorithm to pick from.
# We will handle breaks visually in the template or via a fixed schedule utility.

ACADEMIC_SLOTS = [
    (time(10, 0), time(11, 0)),    # Slot 0
    (time(11, 0), time(12, 0)),    # Slot 1
    # Lunch Break Gap
    (time(12, 45), time(13, 45)),  # Slot 2 (12:45 PM - 1:45 PM)
    (time(13, 45), time(14, 45)),  # Slot 3 (1:45 PM - 2:45 PM)
    # Tea Break Gap
    (time(15, 0), time(16, 0)),    # Slot 4 (3:00 PM - 4:00 PM)
    (time(16, 0), time(17, 0)),    # Slot 5 (4:00 PM - 5:00 PM)
]

CLASS_CONFIG = {
    'tyco_a': {'input': TycoAInput, 'timetable': TycoATimetable, 'name': 'TYCO A'},
    'tyco_b': {'input': TycoBInput, 'timetable': TycoBTimetable, 'name': 'TYCO B'},
    'syco_a': {'input': SycoAInput, 'timetable': SycoATimetable, 'name': 'SYCO A'},
    'syco_b': {'input': SycoBInput, 'timetable': SycoBTimetable, 'name': 'SYCO B'},
}

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

    # 2. Fetch Inputs & Categorize
    # 2. Fetch Inputs & Categorize
    all_inputs = list(InputModel.objects.all())
    
    # Logic Update: A single input can have BOTH Theory and Practical credits.
    # We don't split inputs into "labs" list and "theories" list anymore.
    # We iterate all inputs to build requirements.
    
    # Expand requirements
    # 1 Theory Credit = 1 Hour (1 Slot)
    theory_pool = []
    
    # Practical Requirements: (InputObj, count_of_blocks)
    # 2 Practical Credits = 1 Block of 2 hours.
    lab_reqs = {} 

    for inp in all_inputs:
        # Theory
        for _ in range(inp.theory_credits):
            theory_pool.append(inp)
            
        # Practical
        # If practical_credits = 2, we need 1 block.
        # If practical_credits = 4, we need 2 blocks.
        if inp.practical_credits > 0:
            blocks_needed = inp.practical_credits // 2
            if blocks_needed > 0:
                lab_reqs[inp.id] = blocks_needed
                
    random.shuffle(theory_pool)
    
    # Slot Definitions relative to ACADEMIC_SLOTS list
    # Practical Candidates: (0,1), (2,3), (4,5) -> These are continuous pairs
    
    days_list = [d[0] for d in DAYS] # ['Monday', 'Tuesday'...]
    
    # Grid Initialization: (Day, SlotIndex) -> Entry
    grid = {} 
    
    # --- STEP A: SCHEDULE PRACTICALS ---
    # Create per-batch pools for practicals
    # Each item is the Input Object itself. Blocks needed = practical_credits // 2
    lab_pools = {'A1': [], 'A2': [], 'A3': []}
    
    for inp in all_inputs:
        blocks = inp.practical_credits // 2
        for _ in range(blocks):
            for batch in ['A1', 'A2', 'A3']:
                lab_pools[batch].append(inp) # Add input object reference
                
    # Shuffle pools initially
    for b in lab_pools:
        random.shuffle(lab_pools[b])

    # We need to fill at most 1 PR block per day (Mon-Sat = 6 blocks total)
    # Total requirements should be ~6 per batch.
    
    # Iterate through days
    # Try different start slots per day to vary time?
    # Standard: Start 0, 2, 4.
    
    # Sort inputs by practical credits initially to load heavy items first?
    # Actually just shuffle, we want to solve fully.
    
    for day in days_list:
        possible_starts = [0, 2, 4]
        random.shuffle(possible_starts)
        
        placed_pr = False
        
        for start_slot in possible_starts:
            s1 = start_slot
            s2 = start_slot + 1
            if (day, s1) in grid or (day, s2) in grid:
                continue

            # Check if pools are empty
            if not lab_pools['A1'] or not lab_pools['A2'] or not lab_pools['A3']:
                break
                
            # Create all valid combinations from available pools
            # Use smaller sample if pools are huge, but likely < 10 items.
            # itertools.product generates tuples (poolA1_item, poolA2_item, poolA3_item)
            
            # Optimization: To avoid huge product if pools grow, cap at 200 via islice?
            # Or just shuffle the product list.
            
            p1 = lab_pools['A1']
            p2 = lab_pools['A2']
            p3 = lab_pools['A3']
            
            # Generate all combinations
            # Start generator
            gen = itertools.product(p1, p2, p3)
            
            # To randomize, we can convert to list. Safe for small N.
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
                # Check for both hours
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
                # Remove FIRST instance of object found in pool list
                lab_pools['A1'].remove(found_trio[0])
                lab_pools['A2'].remove(found_trio[1])
                lab_pools['A3'].remove(found_trio[2])
                
                placed_pr = True
                break
        
        # Limit 1 PR block per day
        if placed_pr:
            continue 
            
    # --- STEP B: SCHEDULE THEORY ---
    # Improve standard shuffle with daily limits
    
    # Track daily counts: (day, subject_id) -> count
    subject_daily_counts = {} 
    
    for day in days_list:
        available_slots = [i for i in range(len(ACADEMIC_SLOTS)) if (day, i) not in grid]
        
        # Sort slots: Fill morning/afternoon evenly? Random is fine.
        random.shuffle(available_slots)
        
        for slot_idx in available_slots:
            if not theory_pool: break
            
            # Try to find a valid subject for this slot
            placed_t = None
            
            # Iterate through pool to find best candidate
            # Prioritize subjects that haven't been taught today
            
            # Snapshot of pool to iterate safely
            # We want to pick `i` such that we can pop it.
            
            candidates_indices = list(range(len(theory_pool)))
            random.shuffle(candidates_indices)
            
            for i in candidates_indices:
                candidate = theory_pool[i]
                start_time = ACADEMIC_SLOTS[slot_idx][0]
                
                # 1. Conflict Check
                if check_single_conflict(candidate.teacher_name, day, start_time, class_key):
                    continue
                    
                # 2. Daily Limit Check (Max 2 per day)
                # Key for subject? ID or Name.
                s_key = (day, candidate.id)
                current_count = subject_daily_counts.get(s_key, 0)
                if current_count >= 2:
                    continue
                
                # Found valid
                placed_t = candidate
                theory_pool.pop(i) # Remove from pool
                
                # Update counters
                subject_daily_counts[s_key] = current_count + 1
                break
            
            if placed_t:
                grid[(day, slot_idx)] = {'type': 'TH', 'subject': placed_t, 'batch': 'ALL'}
            else:
                 # Could not fill slot with current pool (conflicts or limits)
                 # Leave empty for Extra lecture
                 pass
                
    # --- STEP C: FILL GAPS WITH EXTRA LECTURES ---
    # Collect all theor subjects to pick from for extras
    extra_candidates = list(all_inputs) 
    
    for day in days_list:
        for i in range(len(ACADEMIC_SLOTS)):
            if (day, i) not in grid:
                # Pick a random subject for extra lecture
                if extra_candidates:
                    rand_subj = random.choice(extra_candidates)
                    grid[(day, i)] = {'type': 'EXTRA', 'subject': rand_subj, 'batch': 'ALL'}
                else:
                    # Fallback if no inputs
                    grid[(day, i)] = {'type': 'FILLER', 'subject_name': 'Free', 'batch': 'ALL'}

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
        "Essence Of Indian Constitution": "EIC"
    }
    
    def get_abbr(name):
        return SUBJECT_ABBR.get(name, name[:3].upper())

    # --- STEP D: SAVE TO DB ---
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
