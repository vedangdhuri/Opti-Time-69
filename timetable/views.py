from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import AcademicClass, Day, TimeSlot, TimetableEntry


def generate_timetable_view(request, class_id):
    """
    Regenerate the full timetable for a class.
    Reads `allow_extra` from the POST body (checkbox in input.html).
    """
    from .services import generate_timetable

    allow_extra = request.POST.get("allow_extra") == "on"
    generate_timetable(class_id, allow_extra=allow_extra)
    return redirect("view_timetable", class_id=class_id)


def add_extra_lectures_view(request, class_id):
    """
    Admin action: fill any remaining empty slots with extra lectures
    WITHOUT re-generating the whole timetable.
    Only responds to POST requests for safety.
    """
    from .services import fill_extra_lectures

    if request.method == "POST":
        fill_extra_lectures(class_id)
        messages.success(request, "Extra lectures have been added to empty slots.")
    return redirect("view_timetable", class_id=class_id)


def view_timetable(request, class_id):
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    days = Day.objects.all()
    slots = list(TimeSlot.objects.all().order_by("start_time"))

    all_entries = TimetableEntry.objects.filter(
        academic_class=academic_class
    ).select_related("subject", "batch", "time_slot", "day")

    # Map: day_id → slot_id → list of entries
    data_map = {d.id: {s.id: [] for s in slots} for d in days}
    for e in all_entries:
        data_map[e.day_id][e.time_slot_id].append(e)

    # Calculate Merges (Rowspans)
    merged_info = {
        d.id: {s.id: {"rowspan": 1, "skipped": False} for s in slots} for d in days
    }

    for d in days:
        for i in range(len(slots) - 1):
            s_curr = slots[i]
            s_next = slots[i + 1]

            entries_curr = data_map[d.id][s_curr.id]
            entries_next = data_map[d.id][s_next.id]

            if entries_curr and entries_next:
                if not entries_curr[0].is_break and not entries_next[0].is_break:
                    should_merge = False

                    # Merge adjacent practical blocks (same batch–subject pairs)
                    if len(entries_curr) > 1 and len(entries_next) > 1:
                        curr_set = set((e.batch_id, e.subject_id) for e in entries_curr)
                        next_set = set((e.batch_id, e.subject_id) for e in entries_next)
                        if curr_set == next_set:
                            should_merge = True

                    if should_merge and not merged_info[d.id][s_curr.id]["skipped"]:
                        merged_info[d.id][s_curr.id]["rowspan"] = 2
                        merged_info[d.id][s_next.id]["skipped"] = True

    # Build Grid for Template
    timetable_grid = []
    unique_subjects = set()

    for slot in slots:
        row_data = {}
        for day in days:
            entries = data_map[day.id][slot.id]
            info = merged_info[day.id][slot.id]

            for e in entries:
                if e.subject:
                    unique_subjects.add(e.subject)

            row_data[day] = {
                "entries": entries,
                "rowspan": info["rowspan"],
                "skipped": info["skipped"],
                "is_break": bool(entries and entries[0].is_break),
            }
        timetable_grid.append((slot, row_data))

    break_slots = {}
    for slot, row in timetable_grid:
        all_break = True
        has_data = False
        for day in days:
            if row[day]["entries"]:
                has_data = True
            if not row[day]["is_break"]:
                all_break = False
        if not has_data:
            all_break = False
        break_slots[slot] = all_break

    context = {
        "academic_class": academic_class,
        "days": days,
        "slots": slots,
        "timetable_grid": timetable_grid,
        "break_slots": break_slots,
        "unique_subjects": sorted(list(unique_subjects), key=lambda s: s.code),
    }

    return render(request, "timetable/view_timetable.html", context)
