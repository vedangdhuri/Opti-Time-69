from django.shortcuts import render, redirect
from .models import AcademicClass, Day, TimeSlot, TimetableEntry

def generate_timetable_view(request, class_id):
    from .services import generate_timetable
    generate_timetable(class_id)
    return redirect("view_timetable", class_id=class_id)

def view_timetable(request, class_id):
    academic_class = AcademicClass.objects.get(id=class_id)
    days = Day.objects.all()
    slots = list(TimeSlot.objects.all().order_by("start_time"))

    # Need to verify if context is passed correctly
    all_entries = TimetableEntry.objects.filter(academic_class=academic_class).select_related('subject', 'batch', 'time_slot', 'day')
    
    # Map: day_id -> slot_id -> list of entries
    data_map = {d.id: {s.id: [] for s in slots} for d in days}
    for e in all_entries:
        data_map[e.day_id][e.time_slot_id].append(e)

    # Calculate Merges (Rowspans)
    merged_info = {d.id: {s.id: {'rowspan': 1, 'skipped': False} for s in slots} for d in days}
    
    for d in days:
        for i in range(len(slots) - 1):
            s_curr = slots[i]
            s_next = slots[i+1]
            
            entries_curr = data_map[d.id][s_curr.id]
            entries_next = data_map[d.id][s_next.id]
            
            # Check merge conditions
            if entries_curr and entries_next:
                if not entries_curr[0].is_break and not entries_next[0].is_break:
                    # Merge if it's a batch practical block (entries > 1) 
                    # OR same single subject (Theory block)
                    should_merge = False
                    
                    if len(entries_curr) > 1 and len(entries_next) > 1:
                        curr_set = set((e.batch_id, e.subject_id) for e in entries_curr)
                        next_set = set((e.batch_id, e.subject_id) for e in entries_next)
                        if curr_set == next_set:
                            should_merge = True
                    
                    # Optional: Merge theory if same subject? (Usually not requested but good for 2hr lectures)
                    # if len(entries_curr) == 1 and len(entries_next) == 1:
                    #     if entries_curr[0].subject_id == entries_next[0].subject_id and entries_curr[0].subject_id:
                    #          should_merge = True

                    if should_merge and not merged_info[d.id][s_curr.id]['skipped']:
                         merged_info[d.id][s_curr.id]['rowspan'] = 2
                         merged_info[d.id][s_next.id]['skipped'] = True

    # Build Grid for Template
    timetable_grid = []
    unique_subjects = set()
    
    for slot in slots:
        row_data = {}
        for day in days:
            entries = data_map[day.id][slot.id]
            info = merged_info[day.id][slot.id]
            
            for e in entries:
                if e.subject: unique_subjects.add(e.subject)
            
            row_data[day] = {
                'entries': entries,
                'rowspan': info['rowspan'],
                'skipped': info['skipped'],
                'is_break': bool(entries and entries[0].is_break)
            }
        timetable_grid.append((slot, row_data))
        
    break_slots = {}
    for slot, row in timetable_grid:
        all_break = True
        has_data = False
        for day in days:
             if row[day]['entries']: has_data = True
             if not row[day]['is_break']:
                 all_break = False
        if not has_data: all_break = False
        break_slots[slot] = all_break

    context = {
        "academic_class": academic_class,
        "days": days,
        "slots": slots,
        "timetable_grid": timetable_grid,
        "break_slots": break_slots,
        "unique_subjects": sorted(list(unique_subjects), key=lambda s: s.code)
    }

    return render(request, "timetable/view_timetable.html", context)
