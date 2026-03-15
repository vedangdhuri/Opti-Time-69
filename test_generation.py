import os
import django
import random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "timetable.settings")
django.setup()

from class_timetable.utils import (
    CLASS_CONFIG,
    generate_timetable_for_class,
    validate_workload_distribution,
)

print("=== DELETING ALL TIMETABLES FIRST ===")
for k, cfg in CLASS_CONFIG.items():
    cfg["timetable"].objects.all().delete()
    print(f"Deleted {k}")

class_keys = list(CLASS_CONFIG.keys())

best_deficit = 9999
best_order = []

for attempt in range(1, 20):
    print(f"\n--- ATTEMPT {attempt} ---")

    # Delete all again
    for k, cfg in CLASS_CONFIG.items():
        cfg["timetable"].objects.all().delete()

    random.shuffle(class_keys)
    print(f"Generating order: {class_keys}")

    for key in class_keys:
        generate_timetable_for_class(key, allow_extra=False)

    total_deficit = 0
    for key in class_keys:
        val = validate_workload_distribution(key)
        total_deficit += val.get("total_practical_deficit", 0) + val.get(
            "total_theory_deficit", 0
        )

    print(f"Total Deficit: {total_deficit}")

    if total_deficit < best_deficit:
        best_deficit = total_deficit
        best_order = list(class_keys)

    if total_deficit == 0:
        print("🎉 Perfect timetable found!")
        break

print(f"\nBest deficit: {best_deficit} with order: {best_order}")
