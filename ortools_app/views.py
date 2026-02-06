# ortools_app\views.py
from django.shortcuts import render
from .models import ClassGroup, Subject, Room, TimeSlot
from .solver import generate_simple_timetable

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def timetable_input(request):
    if request.method == "POST":
        # -------------------------------
        # 1. Read form inputs
        # -------------------------------
        days_count = int(request.POST.get("days", 5))
        slots_per_day = int(request.POST.get("slots", 6))

        # -------------------------------
        # 2. Recreate TimeSlots (FULL WEEK)
        # -------------------------------
        TimeSlot.objects.all().delete()

        for d in range(days_count):
            for s in range(1, slots_per_day + 1):
                TimeSlot.objects.create(
                    day=DAYS[d],
                    slot=s
                )

        # -------------------------------
        # 3. Fetch data for solver
        # -------------------------------
        classes = ClassGroup.objects.all()
        subjects = Subject.objects.all()
        rooms = Room.objects.all()
        slots = TimeSlot.objects.all()

        # Safety check (very important)
        if not classes or not subjects or not rooms or not slots:
            return render(request, "timetable/result.html", {
                "timetable": [],
                "error": "Insufficient data to generate timetable"
            })

        # -------------------------------
        # 4. Call OR-Tools solver
        # -------------------------------
        solution = generate_simple_timetable(
            classes, subjects, rooms, slots
        )

        if not solution:
            return render(request, "timetable/result.html", {
                "timetable": [],
                "error": "No feasible timetable found"
            })

        # -------------------------------
        # 5. Build timetable output
        # -------------------------------
        timetable = []
        for c_id, s_id, r_id, t_id in solution:
            timetable.append({
                "class": ClassGroup.objects.get(id=c_id),
                "subject": Subject.objects.get(id=s_id),
                "room": Room.objects.get(id=r_id),
                "slot": TimeSlot.objects.get(id=t_id),
            })

        return render(request, "timetable/result.html", {
            "timetable": timetable
        })

    # -------------------------------
    # GET request → show input form
    # -------------------------------
    return render(request, "timetable/input.html")
