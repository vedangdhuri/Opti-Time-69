from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .utils import (
    CLASS_CONFIG,
    generate_timetable_for_class,
    ACADEMIC_SLOTS,
    analyze_timetable,
    validate_workload_distribution,
)
from .forms import TycoInputForm, SycoInputForm, FycoInputForm
from .models import TycoTimetable, SycoTimetable, FycoTimetable
from datetime import time


def dashboard(request):
    classes = CLASS_CONFIG.keys()
    context = {"classes": classes, "class_config": CLASS_CONFIG}
    return render(request, "class_timetable/dashboard.html", context)


def input_data(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg["input"]

    form_map = {
        "tyco": TycoInputForm,
        "syco": SycoInputForm,
        "fyco": FycoInputForm,
    }
    FormClass = form_map.get(class_key)

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Input added for {cfg['name']}")
            return redirect("class_timetable:input_data", class_key=class_key)
    else:
        form = FormClass()

    existing_inputs = InputModel.objects.all()

    return render(
        request,
        "class_timetable/input.html",
        {
            "class_key": class_key,
            "class_name": cfg["name"],
            "form": form,
            "inputs": existing_inputs,
        },
    )


def delete_input(request, class_key, input_id):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg["input"]

    input_obj = get_object_or_404(InputModel, id=input_id)
    input_obj.delete()
    messages.success(request, f"Input deleted for {cfg['name']}")
    return redirect("class_timetable:input_data", class_key=class_key)


def generate_timetable_view(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    success, msg = generate_timetable_for_class(class_key)
    if success:
        messages.success(request, f"Timetable generated for {class_key}")
    else:
        messages.error(request, f"Error: {msg}")

    return redirect("class_timetable:view_timetable", class_key=class_key)


def generate_all_timetables_view(request):
    """
    Generates timetables for all classes sequentially.
    This ensures the cross-class conflict solver can correctly avoid any
    teacher double-booking across TYCO, SYCO, and FYCO.
    """
    successes = []
    errors = []
    for class_key in CLASS_CONFIG.keys():
        success, msg = generate_timetable_for_class(class_key)
        if success:
            successes.append(CLASS_CONFIG[class_key]["name"])
        else:
            errors.append(f"{CLASS_CONFIG[class_key]['name']}: {msg}")

    if successes:
        messages.success(
            request,
            f"Successfully generated all timetables for: {', '.join(successes)}",
        )
    if errors:
        messages.error(request, f"Errors during generation: {'; '.join(errors)}")

    return redirect("class_timetable:dashboard")


def view_all_timetables_view(request):
    """Renders all three class timetables on a single page."""
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    view_rows = [
        {
            "start": time(10, 0),
            "end": time(11, 0),
            "label": "10:00 am to 11:00 am",
            "type": "slot",
        },
        {
            "start": time(11, 0),
            "end": time(12, 0),
            "label": "11:00 am to 12:00 pm",
            "type": "slot",
        },
        {
            "label": "LUNCH BREAK",
            "type": "break",
            "start": time(12, 0),
            "end": time(12, 45),
        },
        {
            "start": time(12, 45),
            "end": time(13, 45),
            "label": "12:45 pm to 01:45 pm",
            "type": "slot",
        },
        {
            "start": time(13, 45),
            "end": time(14, 45),
            "label": "01:45 pm to 02:45 pm",
            "type": "slot",
        },
        {
            "label": "TEA BREAK",
            "type": "break",
            "start": time(14, 45),
            "end": time(15, 0),
        },
        {
            "start": time(15, 0),
            "end": time(16, 0),
            "label": "03:00 pm to 04:00 pm",
            "type": "slot",
        },
        {
            "start": time(16, 0),
            "end": time(17, 0),
            "label": "04:00 pm to 05:00 pm",
            "type": "slot",
        },
    ]

    all_timetables = []
    for class_key, cfg in CLASS_CONFIG.items():
        TimetableModel = cfg["timetable"]
        all_entries = TimetableModel.objects.all()
        data_map = {}
        for entry in all_entries:
            k = (entry.day, entry.start_time)
            data_map.setdefault(k, []).append(entry)

        final_rows = []
        covered_cells = set()
        for r_idx, r in enumerate(view_rows):
            row_data = {
                "label": r["label"],
                "type": r["type"],
                "start": r.get("start"),
                "end": r.get("end"),
                "days": [],
            }
            if r["type"] == "slot":
                t_start = r["start"]
                for day in DAY_ORDER:
                    if (r_idx, day) in covered_cells:
                        row_data["days"].append({"skipped": True})
                        continue
                    entries = sorted(
                        data_map.get((day, t_start), []), key=lambda x: x.batch
                    )
                    is_practical = len(entries) > 1
                    rowspan = 1
                    if (
                        is_practical
                        and r_idx in [0, 3, 6]
                        and (r_idx + 1) < len(view_rows)
                    ):
                        nxt = view_rows[r_idx + 1]
                        if (
                            nxt["type"] == "slot"
                            and len(data_map.get((day, nxt["start"]), [])) > 1
                        ):
                            rowspan = 2
                            covered_cells.add((r_idx + 1, day))
                    row_data["days"].append(
                        {
                            "entries": entries,
                            "is_practical": is_practical,
                            "rowspan": rowspan,
                            "skipped": False,
                        }
                    )
            final_rows.append(row_data)

        all_timetables.append(
            {
                "class_name": cfg["name"],
                "class_key": class_key,
                "timetable_rows": final_rows,
                "has_data": bool(all_entries),
            }
        )

    return render(
        request,
        "class_timetable/all_timetables.html",
        {"all_timetables": all_timetables, "days": DAY_ORDER},
    )


def validate_workload_view(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    cfg = CLASS_CONFIG[class_key]
    validation = validate_workload_distribution(class_key)

    return render(
        request,
        "class_timetable/validation.html",
        {"class_name": cfg["name"], "class_key": class_key, "validation": validation},
    )


def overall_analytics_view(request):
    results = {}
    for class_key in CLASS_CONFIG:
        # Check if timetable has entries? Or just run analysis
        # analysis handles empty timetable gracefully (counts 0)
        results[class_key] = analyze_timetable(class_key)
        results[class_key]["name"] = CLASS_CONFIG[class_key]["name"]
        results[class_key]["class_key"] = class_key

    return render(
        request, "class_timetable/overall_analytics.html", {"results": results}
    )


def overall_validation_view(request):
    results = {}
    for class_key in CLASS_CONFIG:
        results[class_key] = validate_workload_distribution(class_key)
        results[class_key]["name"] = CLASS_CONFIG[class_key]["name"]
        results[class_key]["class_key"] = class_key

    return render(
        request, "class_timetable/overall_validation.html", {"results": results}
    )


def analytics_view(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    cfg = CLASS_CONFIG[class_key]
    analysis = analyze_timetable(class_key)

    return render(
        request,
        "class_timetable/analytics.html",
        {"class_name": cfg["name"], "class_key": class_key, "analysis": analysis},
    )


def view_timetable(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg["timetable"]

    # Predefined Week Days in Order
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    # 1. Build Slot List including Breaks for Display
    # Match ACADEMIC_SLOTS from utils + insert breaks

    def fmt(t):
        return t.strftime("%I:%M %p")

    # Define rows manually to match standard output structure
    view_rows = [
        {
            "start": time(10, 0),
            "end": time(11, 0),
            "label": "10:00 am to 11:00 am",
            "type": "slot",
        },
        {
            "start": time(11, 0),
            "end": time(12, 0),
            "label": "11:00 am to 12:00 pm",
            "type": "slot",
        },
        {
            "label": "LUNCH BREAK",
            "type": "break",
            "start": time(12, 0),
            "end": time(12, 45),
        },
        {
            "start": time(12, 45),
            "end": time(13, 45),
            "label": "12:45 pm to 01:45 pm",
            "type": "slot",
        },
        {
            "start": time(13, 45),
            "end": time(14, 45),
            "label": "01:45 pm to 02:45 pm",
            "type": "slot",
        },
        {
            "label": "TEA BREAK",
            "type": "break",
            "start": time(14, 45),
            "end": time(15, 0),
        },
        {
            "start": time(15, 0),
            "end": time(16, 0),
            "label": "03:00 pm to 04:00 pm",
            "type": "slot",
        },
        {
            "start": time(16, 0),
            "end": time(17, 0),
            "label": "04:00 pm to 05:00 pm",
            "type": "slot",
        },
    ]

    # 2. Fetch all entries
    all_entries = TimetableModel.objects.all()

    # 3. Pivot Data: Map (Day, StartTime) -> Data
    data_map = {}
    for entry in all_entries:
        k = (entry.day, entry.start_time)
        if k not in data_map:
            data_map[k] = []
        data_map[k].append(entry)

    # 4. Populate rows with day-wise data
    final_rows = []

    # Track covered cells: (row_index, day)
    covered_cells = set()

    for r_idx, r in enumerate(view_rows):
        row_data = {
            "label": r["label"],
            "type": r["type"],
            "start": r.get("start"),
            "end": r.get("end"),
            "days": [],
        }

        if r["type"] == "slot":
            t_start = r["start"]

            for day in DAY_ORDER:
                if (r_idx, day) in covered_cells:
                    row_data["days"].append({"skipped": True})
                    continue

                entries = data_map.get((day, t_start), [])

                # Sort by batch
                entries.sort(key=lambda x: x.batch)

                is_practical = len(entries) > 1
                rowspan = 1

                # Check for merge (Practical Block of 2 hours)
                # Rows 0, 3, 6 are start of blocks in our view_rows structure
                if is_practical and r_idx in [0, 3, 6] and (r_idx + 1) < len(view_rows):
                    next_row = view_rows[r_idx + 1]
                    if next_row["type"] == "slot":
                        next_t_start = next_row["start"]
                        next_entries = data_map.get((day, next_t_start), [])

                        # If next slot is also practical, assume valid block merge
                        if len(next_entries) > 1:
                            rowspan = 2
                            covered_cells.add((r_idx + 1, day))

                cell_info = {
                    "entries": entries,
                    "is_practical": is_practical,
                    "rowspan": rowspan,
                    "skipped": False,
                }
                row_data["days"].append(cell_info)

        final_rows.append(row_data)

    return render(
        request,
        "class_timetable/view.html",
        {
            "class_name": cfg["name"],
            "class_key": class_key,
            "timetable_rows": final_rows,
            "days": DAY_ORDER,
        },
    )


def delete_timetable(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect("class_timetable:dashboard")

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["POST"])

    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg["timetable"]
    TimetableModel.objects.all().delete()
    messages.warning(request, f"Timetable deleted for {cfg['name']}")
    return redirect("class_timetable:dashboard")


def teacher_timetable_view(request):
    """Shows individual timetables for every teacher, aggregated across all classes."""
    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    VIEW_ROWS = [
        {
            "start": time(10, 0),
            "end": time(11, 0),
            "label": "10:00 am to 11:00 am",
            "type": "slot",
        },
        {
            "start": time(11, 0),
            "end": time(12, 0),
            "label": "11:00 am to 12:00 pm",
            "type": "slot",
        },
        {
            "start": time(12, 0),
            "end": time(12, 45),
            "label": "LUNCH BREAK",
            "type": "break",
        },
        {
            "start": time(12, 45),
            "end": time(13, 45),
            "label": "12:45 pm to 01:45 pm",
            "type": "slot",
        },
        {
            "start": time(13, 45),
            "end": time(14, 45),
            "label": "01:45 pm to 02:45 pm",
            "type": "slot",
        },
        {
            "start": time(14, 45),
            "end": time(15, 0),
            "label": "TEA BREAK",
            "type": "break",
        },
        {
            "start": time(15, 0),
            "end": time(16, 0),
            "label": "03:00 pm to 04:00 pm",
            "type": "slot",
        },
        {
            "start": time(16, 0),
            "end": time(17, 0),
            "label": "04:00 pm to 05:00 pm",
            "type": "slot",
        },
    ]

    # Class metadata for badge colours
    CLASS_META = [
        {"model": TycoTimetable, "label": "TYCO", "color": "primary"},
        {"model": SycoTimetable, "label": "SYCO", "color": "success"},
        {"model": FycoTimetable, "label": "FYCO", "color": "warning"},
    ]

    # Collect ALL entries annotated with class info
    all_entries = []
    for meta in CLASS_META:
        for entry in meta["model"].objects.all():
            all_entries.append(
                {
                    "teacher_name": entry.teacher_name.strip(),
                    "day": entry.day,
                    "start_time": entry.start_time,
                    "subject_name": entry.subject_name,
                    "batch": entry.batch,
                    "class_label": meta["label"],
                    "class_color": meta["color"],
                }
            )

    # Group by teacher
    teacher_map = {}
    for e in all_entries:
        name = e["teacher_name"]
        if name not in teacher_map:
            teacher_map[name] = []
        teacher_map[name].append(e)

    # Build per-teacher grid
    teachers = []
    for teacher_name in sorted(teacher_map.keys()):
        entries = teacher_map[teacher_name]

        # Pivot: (day, start_time) -> list of entries
        data_map = {}
        for e in entries:
            k = (e["day"], e["start_time"])
            data_map.setdefault(k, []).append(e)

        covered_cells = set()
        final_rows = []

        for r_idx, r in enumerate(VIEW_ROWS):
            row_data = {
                "label": r["label"],
                "type": r["type"],
                "start": r.get("start"),
                "end": r.get("end"),
                "days": [],
            }

            if r["type"] == "slot":
                t_start = r["start"]
                for day in DAY_ORDER:
                    if (r_idx, day) in covered_cells:
                        row_data["days"].append({"skipped": True})
                        continue

                    cell_entries = data_map.get((day, t_start), [])
                    is_practical = False
                    rowspan = 1

                    # Merge two-hour practical blocks
                    if (
                        len(cell_entries) > 0
                        and r_idx in [0, 3, 6]
                        and (r_idx + 1) < len(VIEW_ROWS)
                    ):
                        next_r = VIEW_ROWS[r_idx + 1]
                        if next_r["type"] == "slot":
                            next_entries = data_map.get((day, next_r["start"]), [])
                            if len(next_entries) > 0:
                                # Check if the first entry matches subject and batch
                                current_e = cell_entries[0]
                                next_e = next_entries[0]
                                if (
                                    current_e["subject_name"] == next_e["subject_name"]
                                    and current_e["batch"] == next_e["batch"]
                                    and current_e["class_label"]
                                    == next_e["class_label"]
                                ):
                                    is_practical = True
                                    rowspan = 2
                                    covered_cells.add((r_idx + 1, day))

                    row_data["days"].append(
                        {
                            "entries": cell_entries,
                            "is_practical": is_practical,
                            "rowspan": rowspan,
                            "skipped": False,
                        }
                    )

            final_rows.append(row_data)

        teachers.append(
            {
                "name": teacher_name,
                "rows": final_rows,
            }
        )

    return render(
        request,
        "class_timetable/teacher_timetable.html",
        {
            "teachers": teachers,
            "days": DAY_ORDER,
            "has_data": bool(teachers),
        },
    )
