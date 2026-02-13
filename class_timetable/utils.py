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
        
        # Limit 1 PR block per day
        if placed_pr:
            continue 
            
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
                
    # --- STEP C: FILL GAPS WITH EXTRA LECTURES ---
    extra_candidates = list(all_inputs) 
    
    for day in days_list:
        for i in range(len(ACADEMIC_SLOTS)):
            if (day, i) not in grid:
                # Pick a random subject for extra lecture
                # Only if we really can't fill with theory
                if extra_candidates:
                    rand_subj = random.choice(extra_candidates)
                    grid[(day, i)] = {'type': 'EXTRA', 'subject': rand_subj, 'batch': 'ALL'}
                else:
                    grid[(day, i)] = {'type': 'FILLER', 'subject_name': 'Free', 'batch': 'ALL'}

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
