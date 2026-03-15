from timetable.models import (
    AcademicClass,
    Day,
    TimeSlot,
    Subject,
    Room,
    Batch,
    TimetableEntry,
)
import random


# ---------------------------------------------------------------------------
# Constants — practical sessions each batch must receive per subject
# ---------------------------------------------------------------------------
COURSE_DATA = [
    {"code": "OSY", "th": 5, "pr_sessions": 1},
    {"code": "STE", "th": 4, "pr_sessions": 2},
    {"code": "ENDS", "th": 1, "pr_sessions": 1},
    {"code": "SPI", "th": 0, "pr_sessions": 1},
    {"code": "CLC", "th": 4, "pr_sessions": 1},
]

BATCH_NAMES = ["A1", "A2", "A3"]


def _is_break(slot):
    """Return True if this time‑slot is a break (Lunch / Tea)."""
    return slot.start_time.strftime("%H:%M") in {"12:00", "14:45"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_objects():
    """Ensure Batch and Subject rows exist; return helper maps."""
    batches = []
    for name in BATCH_NAMES:
        b, _ = Batch.objects.get_or_create(name=name)
        batches.append(b)

    subjects_map = {}
    for item in COURSE_DATA:
        sub = Subject.objects.filter(code=item["code"]).first()
        if not sub:
            sub = Subject.objects.create(
                code=item["code"], name=item["code"], subject_type="THEORY"
            )
        subjects_map[item["code"]] = sub

    rooms = list(Room.objects.all())
    if not rooms:
        rooms = [Room.objects.create(room_number="CR-1")]

    return batches, subjects_map, rooms


def _build_practical_blocks(batches, subjects_map):
    """
    Build a list of practical‑block dicts: [{batch_obj: subject_obj, …}, …].

    Each batch gets EXACTLY `pr_sessions` blocks per subject.
    Blocks are paired round‑robin across batches so that within one block,
    no two batches share the same subject (avoids lab conflicts).
    """
    # Fill per‑batch bucket: repeat each subject pr_sessions times
    batch_buckets = {}
    for b in batches:
        bucket = []
        for item in COURSE_DATA:
            sub = subjects_map[item["code"]]
            for _ in range(item["pr_sessions"]):
                bucket.append(sub)
        random.shuffle(bucket)
        batch_buckets[b.name] = bucket

    practical_blocks = []

    # Keep looping until every bucket is drained
    while any(batch_buckets[b.name] for b in batches):
        block_assignment = {}  # {batch_obj: subject_obj}
        used_subjects = set()  # subjects already placed in this block

        for b in batches:
            bucket = batch_buckets[b.name]
            if not bucket:
                continue  # this batch has no more practicals — skip

            # Try to pick a subject not used by another batch in this block
            chosen = None
            for sub in bucket:
                if sub not in used_subjects:
                    chosen = sub
                    break

            # Fall back: allow duplicate subject across batches in same block
            # (only if every remaining subject conflicts — very rare)
            if chosen is None:
                chosen = bucket[0]

            block_assignment[b] = chosen
            bucket.remove(chosen)
            used_subjects.add(chosen)

        if block_assignment:
            practical_blocks.append(block_assignment)

    return practical_blocks


def _place_practical_blocks(academic_class, practical_blocks, days, all_slots, rooms):
    """
    Place each practical block in a 2‑consecutive‑slot window that has no
    existing entry and is not a break slot.
    """
    DURATION = 2

    # Build list of (day, [slot, slot]) candidates
    block_candidates = []
    for d in days:
        for i in range(len(all_slots) - (DURATION - 1)):
            s_pair = all_slots[i : i + DURATION]
            if any(_is_break(s) for s in s_pair):
                continue
            block_candidates.append((d, s_pair))

    random.shuffle(block_candidates)

    for assignment in practical_blocks:
        placed = False
        for idx, (day, s_pair) in enumerate(block_candidates):
            # Check both slots are free
            collision = any(
                TimetableEntry.objects.filter(
                    academic_class=academic_class, day=day, time_slot=s
                ).exists()
                for s in s_pair
            )
            if collision:
                continue

            # Place the block
            for batch, sub in assignment.items():
                r = random.choice(rooms)
                for s in s_pair:
                    TimetableEntry.objects.create(
                        academic_class=academic_class,
                        day=day,
                        time_slot=s,
                        subject=sub,
                        room=r,
                        batch=batch,
                    )
            block_candidates.pop(idx)
            placed = True
            break

        if not placed:
            # No free 2‑slot window found — place each hour individually
            single_free = [
                (d, s)
                for d in days
                for s in all_slots
                if not _is_break(s)
                and not TimetableEntry.objects.filter(
                    academic_class=academic_class, day=d, time_slot=s
                ).exists()
            ]
            random.shuffle(single_free)
            for batch, sub in assignment.items():
                if single_free:
                    day, s = single_free.pop(0)
                    r = random.choice(rooms)
                    TimetableEntry.objects.create(
                        academic_class=academic_class,
                        day=day,
                        time_slot=s,
                        subject=sub,
                        room=r,
                        batch=batch,
                    )


def _place_theory(academic_class, subjects_map, days, all_slots, rooms):
    """Place all theory lectures in remaining free single slots."""
    theory_tasks = []
    for item in COURSE_DATA:
        sub = subjects_map[item["code"]]
        for _ in range(item["th"]):
            theory_tasks.append(sub)
    random.shuffle(theory_tasks)

    single_candidates = [(d, s) for d in days for s in all_slots if not _is_break(s)]
    random.shuffle(single_candidates)

    for sub in theory_tasks:
        for idx, (day, slot) in enumerate(single_candidates):
            if TimetableEntry.objects.filter(
                academic_class=academic_class, day=day, time_slot=slot
            ).exists():
                continue

            r = random.choice(rooms)
            TimetableEntry.objects.create(
                academic_class=academic_class,
                day=day,
                time_slot=slot,
                subject=sub,
                room=r,
                batch=None,
            )
            single_candidates.pop(idx)
            break


def _mark_breaks(academic_class, days, all_slots):
    """Ensure every break slot has a TimetableEntry marked as break."""
    for day in days:
        for slot in all_slots:
            if _is_break(slot):
                TimetableEntry.objects.get_or_create(
                    academic_class=academic_class,
                    day=day,
                    time_slot=slot,
                    defaults={"is_break": True},
                )


def fill_extra_lectures(academic_class_id):
    """
    PHASE 5 (standalone): Fill any remaining empty (non‑break) slots
    with extra lectures. Safe to call on an already‑generated timetable.
    """
    academic_class = AcademicClass.objects.get(id=academic_class_id)
    days = list(Day.objects.all())
    all_slots = list(TimeSlot.objects.all().order_by("start_time"))
    rooms = list(Room.objects.all())
    subjects_list = list(Subject.objects.all())

    if not rooms:
        rooms = [Room.objects.create(room_number="CR-1")]
    if not subjects_list:
        return

    for day in days:
        for slot in all_slots:
            if _is_break(slot):
                continue
            if TimetableEntry.objects.filter(
                academic_class=academic_class, day=day, time_slot=slot
            ).exists():
                continue

            sub = random.choice(subjects_list)
            r = rooms[0]
            TimetableEntry.objects.create(
                academic_class=academic_class,
                day=day,
                time_slot=slot,
                subject=sub,
                room=r,
                batch=None,
                is_extra=True,
            )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_timetable(academic_class_id, allow_extra=False):
    """
    Generate a complete timetable for the given class.

    Phases:
      1. Prepare practical blocks (proper per‑batch distribution)
      2. Place practical blocks (2‑slot contiguous windows)
      3. Place theory lectures (single slots)
      4. Mark break rows
      5. [Optional] Fill empty slots with extra lectures
    """
    academic_class = AcademicClass.objects.get(id=academic_class_id)

    # ── Setup ──────────────────────────────────────────────────────────────
    batches, subjects_map, rooms = _setup_objects()
    days = list(Day.objects.all())
    all_slots = list(TimeSlot.objects.all().order_by("start_time"))

    # Clear previously generated data for this class
    TimetableEntry.objects.filter(academic_class=academic_class).delete()

    # ── Phase 1: Build practical blocks ───────────────────────────────────
    practical_blocks = _build_practical_blocks(batches, subjects_map)

    # ── Phase 2: Place practical blocks ───────────────────────────────────
    _place_practical_blocks(academic_class, practical_blocks, days, all_slots, rooms)

    # ── Phase 3: Place theory ─────────────────────────────────────────────
    _place_theory(academic_class, subjects_map, days, all_slots, rooms)

    # ── Phase 4: Mark breaks ──────────────────────────────────────────────
    _mark_breaks(academic_class, days, all_slots)

    # ── Phase 5: Extra lectures (optional) ────────────────────────────────
    if allow_extra:
        fill_extra_lectures(academic_class_id)
