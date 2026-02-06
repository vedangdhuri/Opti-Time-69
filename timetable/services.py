from timetable.models import (
    AcademicClass, Day, TimeSlot, Subject,
    Room, Batch, TimetableEntry
)
import random

def generate_timetable(academic_class_id):
    academic_class = AcademicClass.objects.get(id=academic_class_id)
    
    # 1. Setup Data
    course_data = [
        {"code": "OSY",  "th": 5, "pr_sessions": 1},
        {"code": "STE",  "th": 4, "pr_sessions": 2},
        {"code": "ENDS", "th": 1, "pr_sessions": 1},
        {"code": "SPI",  "th": 0, "pr_sessions": 1}, 
        {"code": "CLC",  "th": 4, "pr_sessions": 1}
    ]
    
    # Batches
    batch_names = ["A1", "A2", "A3"]
    batches = []
    for b_name in batch_names:
        batch, _ = Batch.objects.get_or_create(name=b_name)
        batches.append(batch)

    # Subjects
    subjects_map = {}
    for item in course_data:
        sub = Subject.objects.filter(code=item["code"]).first()
        if not sub:
            sub = Subject.objects.create(code=item["code"], name=item["code"], subject_type="THEORY")
        subjects_map[item["code"]] = sub

    # Rooms
    rooms = list(Room.objects.all())
    if not rooms:
        rooms = [Room.objects.create(room_number="CR-1")]

    days = list(Day.objects.all())
    all_slots = list(TimeSlot.objects.all().order_by("start_time"))
    
    # Clear Old Data
    TimetableEntry.objects.filter(academic_class=academic_class).delete()

    # --- PHASE 1: PREPARE PRACTICAL TRIPLETS ---
    batch_buckets = {b.name: [] for b in batches}
    for b in batches:
        for item in course_data:
            for _ in range(item["pr_sessions"]):
                batch_buckets[b.name].append(subjects_map[item["code"]])
    
    practical_blocks = [] # List of {batch: subject} dicts
    
    for k in batch_buckets:
        random.shuffle(batch_buckets[k])
        
    max_sessions = 6 
    
    for _ in range(max_sessions):
        block_assignment = {}
        used_subs = set()
        
        for b in batches:
            bucket = batch_buckets[b.name]
            chosen = None
            for sub in bucket:
                if sub not in used_subs:
                    chosen = sub
                    break
            
            if not chosen and bucket:
                chosen = bucket[0]
            
            if chosen:
                block_assignment[b] = chosen
                bucket.remove(chosen)
                used_subs.add(chosen)
                
        if block_assignment:
            practical_blocks.append(block_assignment)

    # --- PHASE 2: PLACE PRACTICAL BLOCKS ---
    def is_break(s):
        return s.start_time.strftime("%H:%M") in ["12:00", "14:45"]
        
    duration = 2
    
    block_candidates = []
    for d in days:
        for i in range(len(all_slots) - (duration - 1)):
            s_pair = all_slots[i:i+duration]
            if any(is_break(s) for s in s_pair): continue
            block_candidates.append((d, s_pair))
            
    random.shuffle(block_candidates)
    
    for assignment in practical_blocks:
        placed = False
        for i, (day, s_pair) in enumerate(block_candidates):
            collision = False
            for s in s_pair:
                if TimetableEntry.objects.filter(academic_class=academic_class, day=day, time_slot=s).exists():
                    collision = True; break
            
            if not collision:
                for batch, sub in assignment.items():
                    r = random.choice(rooms) 
                    for s in s_pair:
                         TimetableEntry.objects.create(
                            academic_class=academic_class,
                            day=day,
                            time_slot=s,
                            subject=sub,
                            room=r,
                            batch=batch
                        )
                block_candidates.pop(i)
                placed = True
                break
    
    # --- PHASE 3: THEORY ---
    theory_tasks = []
    for item in course_data:
        for _ in range(item["th"]):
            theory_tasks.append(subjects_map[item["code"]])
    random.shuffle(theory_tasks)
    
    single_candidates = []
    for d in days:
        for s in all_slots:
            if not is_break(s):
               single_candidates.append((d, s))
    random.shuffle(single_candidates)
    
    for sub in theory_tasks:
        placed = False
        for day, slot in single_candidates:
            if placed: break
            if TimetableEntry.objects.filter(academic_class=academic_class, day=day, time_slot=slot).exists():
                continue
                
            r = random.choice(rooms)
            TimetableEntry.objects.create(
                academic_class=academic_class,
                day=day,
                time_slot=slot,
                subject=sub,
                room=r,
                batch=None
            )
            placed = True

    # --- PHASE 4: FILL BREAKS ---
    for day in days:
        for slot in all_slots:
            if is_break(slot):
                 if not TimetableEntry.objects.filter(academic_class=academic_class, day=day, time_slot=slot, is_break=True).exists():
                     TimetableEntry.objects.create(
                        academic_class=academic_class,
                        day=day,
                        time_slot=slot,
                        is_break=True
                     )

    # --- PHASE 5: FILL GAPS WITH EXTRA LECTURES ---
    available_subjects = list(subjects_map.values())
    
    for day in days:
        for slot in all_slots:
            if is_break(slot): continue
            
            if not TimetableEntry.objects.filter(academic_class=academic_class, day=day, time_slot=slot).exists():
                 if available_subjects:
                     sub = random.choice(available_subjects)
                     r = rooms[0]
                     
                     TimetableEntry.objects.create(
                        academic_class=academic_class,
                        day=day,
                        time_slot=slot,
                        subject=sub,
                        room=r,
                        batch=None, 
                        is_extra=True # Mark as extra
                     )
