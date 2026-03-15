from class_timetable.utils import (
    CLASS_CONFIG,
    generate_timetable_for_class,
    validate_workload_distribution,
)
import random

class_keys = list(CLASS_CONFIG.keys())

for attempt in range(5):
    # clear all first
    for k, cfg in CLASS_CONFIG.items():
        cfg["timetable"].objects.all().delete()

    random.shuffle(class_keys)
    print(f"Order: {class_keys}")

    # Generate
    for key in class_keys:
        generate_timetable_for_class(key, allow_extra=False)

    deficits = {
        k: validate_workload_distribution(k).get("total_practical_deficit", 0)
        for k in class_keys
    }
    total = sum(deficits.values())
    print(f"Attempt {attempt} deficits: {deficits}")
    if total == 0:
        print("PERFECT!")
        break
