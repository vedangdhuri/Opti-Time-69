import random
import itertools
from datetime import time
from .models import (
    TycoInput,
    TycoTimetable,
    TycoBInput,
    TycoBTimetable,
    SycoInput,
    SycoTimetable,
    SycoBInput,
    SycoBTimetable,
    FycoInput,
    FycoTimetable,
    FycoBInput,
    FycoBTimetable,
    DAYS,
)

# === CONFIGURATION ===
ACADEMIC_SLOTS = [
    (time(10, 0), time(11, 0)),  # Slot 0
    (time(11, 0), time(12, 0)),  # Slot 1
    (time(12, 45), time(13, 45)),  # Slot 2  (after lunch)
    (time(13, 45), time(14, 45)),  # Slot 3
    (time(15, 0), time(16, 0)),  # Slot 4  (after tea)
    (time(16, 0), time(17, 0)),  # Slot 5
]

# Adjacent slot pairs that can host a 2-hour practical block
ADJACENT_PAIRS = [(0, 1), (2, 3), (4, 5)]

CLASS_CONFIG = {
    "tyco": {"input": TycoInput, "timetable": TycoTimetable, "name": "TYCO A"},
    "tyco_b": {"input": TycoBInput, "timetable": TycoBTimetable, "name": "TYCO B"},
    "syco": {"input": SycoInput, "timetable": SycoTimetable, "name": "SYCO A"},
    "syco_b": {"input": SycoBInput, "timetable": SycoBTimetable, "name": "SYCO B"},
    "fyco": {"input": FycoInput, "timetable": FycoTimetable, "name": "FYCO A"},
    "fyco_b": {"input": FycoBInput, "timetable": FycoBTimetable, "name": "FYCO B"},
}

SUBJECT_ABBR = {
    # TYCO A (Sem V)
    "OPERATING SYSTEM": "OSY",
    "SOFTWARE ENGINEERING": "STE",
    "ENTREPRENEURSHIP DEVELOPMENT AND STARTUPS": "ENDS",
    "SEMINAR AND PROJECT INITIATION COURSE": "SPI",
    "CLOUD COMPUTING": "CLC",
    # TYCO A (Sem VI)
    "Management": "MAN",
    "Mobile Application Development": "MAD",
    "Emerging Trends In Computer & Information Tech.": "ETI",
    "Cilent-Side Scripting": "CSS",
    "Software Testing": "SFT",
    "Capstone Project": "CPE",
    "Network And Information Security": "NIS",
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
    "User Interface Design": "UID",
    # FYCO (Sem I)
    "Basic Mathematics": "BMS",
    "Basic Science (Physics)": "PHY",
    "Basic Science (Chemistry)": "CHY",
    "Communication Skills": "ENG",
    "Engineering Graphics": "EGP",
    "Professional Communication": "POC",
    "Engineering Workshop Practice": "WPC",
    "Fundamentals of ICT": "ICT",
    # FYCO (Sem II)
    "Basic Electrical And Electronics Engineering": "BEE",
    "Programming In 'C'": "PIC",
    "Linux Basics": "BLP",
    "Web Page Designing": "WPD",
    "Applied Mathematics": "AMS",
}


def get_abbr(name):
    if name in SUBJECT_ABBR:
        return SUBJECT_ABBR[name]

    try:
        from .models import MasterSubject

        ms = MasterSubject.objects.filter(subject_name__iexact=name).first()
        if ms and ms.abbreviation:
            return ms.abbreviation.strip().upper()
    except Exception:
        pass

    return name[:3].upper()


def normalize_teacher_name(name):
    return " ".join(str(name).strip().split())


# ──────────────────────────────────────────────────────────────────────────────
# Teacher-conflict helpers
# ──────────────────────────────────────────────────────────────────────────────


def _teachers_in_grid_at(grid, day, start_time):
    busy = set()
    for (g_day, g_slot), g_data in grid.items():
        if g_day != day:
            continue
        if ACADEMIC_SLOTS[g_slot][0] != start_time:
            continue
        t = g_data.get("type", "")
        if t in ("TH", "EXTRA"):
            busy.add(normalize_teacher_name(g_data["subject"].teacher_name))
        elif t == "PR":
            for lab in g_data.get("trio", []):
                busy.add(normalize_teacher_name(lab.teacher_name))
    return busy


def check_teacher_conflict_bulk(
    teacher_list, day, start_time, exclude_class_key, current_grid=None
):
    from django.db.models.functions import Trim

    normalized = [normalize_teacher_name(n) for n in teacher_list]
    normalized_set = set(normalized)

    for key, cfg in CLASS_CONFIG.items():
        if key == exclude_class_key:
            continue
        busy = (
            cfg["timetable"]
            .objects.annotate(trimmed=Trim("teacher_name"))
            .filter(trimmed__in=normalized, day=day, start_time=start_time)
            .exists()
        )
        if busy:
            return True

    if current_grid is not None:
        grid_teachers = _teachers_in_grid_at(current_grid, day, start_time)
        if normalized_set & grid_teachers:
            return True

    return False


def check_single_conflict(
    teacher, day, start_time, exclude_class_key, current_grid=None
):
    return check_teacher_conflict_bulk(
        [teacher], day, start_time, exclude_class_key, current_grid
    )


# ──────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ──────────────────────────────────────────────────────────────────────────────


def generate_timetable_for_class(class_key, allow_extra=True):
    """
    Human-teacher style timetable generator.

    How a human teacher thinks:
    - "I have lab subjects S0, S1, S2 needing N0, N1, N2 sessions each."
    - "Each lab slot: all 3 batches run simultaneously. A1=Sa, A2=Sb, A3=Sc (unique subjects)."
    - "I rotate: next slot A1=Sb, A2=Sc, A3=Sa. This way no batch ever does the same subject."
    - "I count how many total lab windows I need, build that many rotated trios, then place them."

    Phase 1 — Build all required practical sessions as (A1-subj, A2-subj, A3-subj) trios
              using cyclic rotation of practical subjects.
    Phase 2 — Place every session into a free adjacent-pair slot, checking teacher conflicts.
    Phase 3 — Fill remaining free slots with theory.
    Phase 4 — Fill any remaining gaps with Extra lectures or Library.
    """
    if class_key not in CLASS_CONFIG:
        return False, "Invalid Class"

    InputModel = CLASS_CONFIG[class_key]["input"]
    TimetableModel = CLASS_CONFIG[class_key]["timetable"]

    TimetableModel.objects.all().delete()

    all_inputs = list(InputModel.objects.all())
    for inp in all_inputs:
        inp.teacher_name = normalize_teacher_name(inp.teacher_name)

    days_list = [d[0] for d in DAYS]
    grid = {}  # (day, slot_index) → data dict

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 1 — BUILD PRACTICAL SESSION LIST  (rotation-based)
    # ──────────────────────────────────────────────────────────────────────────
    # Gather subjects that have practical work
    lab_subjects = [inp for inp in all_inputs if inp.practical_credits > 0]

    # sessions_queue: list of (subj_A1, subj_A2, subj_A3) tuples
    # Each entry = one 2-hr block that needs a slot in the timetable.
    # We build this by iterating over *all required blocks across all subjects*
    # and rotating which subject goes to which batch.
    sessions_queue = []

    subj_by_id = {s.id: s for s in lab_subjects}

    if lab_subjects:

        class _Lib:
            subject_name = "Library"
            teacher_name = "-"
            id = -1

        lib_obj = _Lib()

        needs = {
            "A1": {s.id: s.practical_credits // 2 for s in lab_subjects},
            "A2": {s.id: s.practical_credits // 2 for s in lab_subjects},
            "A3": {s.id: s.practical_credits // 2 for s in lab_subjects},
        }

        # Safety breakout
        for _ in range(100):
            # Check if all batches have 0 remaining needs
            if all(sum(needs[b].values()) == 0 for b in ["A1", "A2", "A3"]):
                break

            batch_order = ["A1", "A2", "A3"]
            random.shuffle(batch_order)

            this_slot = {"A1": lib_obj, "A2": lib_obj, "A3": lib_obj}
            used_teachers = set()

            for b in batch_order:
                best_s_id = None
                best_count = -1

                # To add organic distribution without getting stuck, we can shuffle
                # equal-count candidates, but sorting first ensures deterministic base
                candidates = list(needs[b].keys())
                random.shuffle(candidates)

                for s_id in candidates:
                    count = needs[b][s_id]
                    if count > 0:
                        t_name = subj_by_id[s_id].teacher_name
                        if t_name not in used_teachers:
                            if count > best_count:
                                best_count = count
                                best_s_id = s_id

                if best_s_id is not None:
                    needs[b][best_s_id] -= 1
                    used_teachers.add(subj_by_id[best_s_id].teacher_name)
                    this_slot[b] = subj_by_id[best_s_id]

            # Append the trio exactly in A1, A2, A3 order
            sessions_queue.append((this_slot["A1"], this_slot["A2"], this_slot["A3"]))

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2 — PLACE PRACTICAL SESSIONS INTO FREE ADJACENT PAIRS
    # ──────────────────────────────────────────────────────────────────────────
    # Build shuffled list of all (day, s1, s2) candidates
    all_pairs = [(day, s1, s2) for day in days_list for s1, s2 in ADJACENT_PAIRS]
    random.shuffle(all_pairs)

    remaining_sessions = list(sessions_queue)

    for day, s1, s2 in all_pairs:
        if not remaining_sessions:
            break
        if (day, s1) in grid or (day, s2) in grid:
            continue

        st1 = ACADEMIC_SLOTS[s1][0]
        st2 = ACADEMIC_SLOTS[s2][0]

        # Try to place the next session that works here (teacher conflict check)
        placed = False
        for idx, session in enumerate(remaining_sessions):
            subj_A1, subj_A2, subj_A3 = session
            teachers = list(
                dict.fromkeys(
                    t
                    for t in [
                        subj_A1.teacher_name,
                        subj_A2.teacher_name,
                        subj_A3.teacher_name,
                    ]
                    if t != "-"
                )
            )
            if check_teacher_conflict_bulk(teachers, day, st1, class_key, grid):
                continue
            if check_teacher_conflict_bulk(teachers, day, st2, class_key, grid):
                continue

            # Valid — commit this session
            trio = [subj_A1, subj_A2, subj_A3]
            grid[(day, s1)] = {"type": "PR", "trio": trio}
            grid[(day, s2)] = {"type": "PR", "trio": trio}
            remaining_sessions.pop(idx)
            placed = True
            break

        # If first choice failed, try any remaining session
        if not placed:
            for idx, session in enumerate(remaining_sessions):
                subj_A1, subj_A2, subj_A3 = session
                teachers = list(
                    dict.fromkeys(
                        t
                        for t in [
                            subj_A1.teacher_name,
                            subj_A2.teacher_name,
                            subj_A3.teacher_name,
                        ]
                        if t != "-"
                    )
                )
                if check_teacher_conflict_bulk(teachers, day, st1, class_key, grid):
                    continue
                if check_teacher_conflict_bulk(teachers, day, st2, class_key, grid):
                    continue
                trio = [subj_A1, subj_A2, subj_A3]
                grid[(day, s1)] = {"type": "PR", "trio": trio}
                grid[(day, s2)] = {"type": "PR", "trio": trio}
                remaining_sessions.pop(idx)
                break

    # ──────────────────────────────────────────────────────────────────────────
    # SLOT RESERVATION — protect free adjacent pairs for unplaced sessions
    # We know exactly how many sessions are left. Reserve that many pairs NOW
    # so Phase 3 (theory) cannot consume them.
    # ──────────────────────────────────────────────────────────────────────────
    reserved_pairs = set()  # (day, s1) keys — first slot of each reserved pair
    if remaining_sessions:
        free_adj = [
            (day, s1, s2)
            for day in days_list
            for s1, s2 in ADJACENT_PAIRS
            if (day, s1) not in grid and (day, s2) not in grid
        ]
        random.shuffle(free_adj)
        for day, s1, s2 in free_adj:
            if len(reserved_pairs) >= len(remaining_sessions):
                break
            reserved_pairs.add((day, s1))

    def _in_reserved(day, slot_idx):
        """True if this slot belongs to a reserved practical pair."""
        for s1, s2 in ADJACENT_PAIRS:
            if slot_idx in (s1, s2) and (day, s1) in reserved_pairs:
                return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3 — THEORY  (skips slots in reserved pairs)
    # ──────────────────────────────────────────────────────────────────────────
    theory_pool = []
    for inp in all_inputs:
        for _ in range(inp.theory_credits):
            theory_pool.append(inp)
    random.shuffle(theory_pool)

    subject_daily_counts = {}

    # First pass: max 2 same-subject per day
    for day in days_list:
        free_slots = [
            i
            for i in range(len(ACADEMIC_SLOTS))
            if (day, i) not in grid and not _in_reserved(day, i)
        ]
        random.shuffle(free_slots)
        for slot_idx in free_slots:
            if not theory_pool:
                break
            start_time = ACADEMIC_SLOTS[slot_idx][0]
            idxs = list(range(len(theory_pool)))
            random.shuffle(idxs)
            for i in idxs:
                cand = theory_pool[i]
                if check_single_conflict(
                    cand.teacher_name, day, start_time, class_key, grid
                ):
                    continue
                s_key = (day, cand.id)
                if subject_daily_counts.get(s_key, 0) >= 2:
                    continue
                grid[(day, slot_idx)] = {"type": "TH", "subject": cand, "batch": "ALL"}
                subject_daily_counts[s_key] = subject_daily_counts.get(s_key, 0) + 1
                theory_pool.pop(i)
                break

    # Theory backfill: relax daily cap to 3, still skip reserved pairs
    if theory_pool:
        all_free = [
            (d, s)
            for d in days_list
            for s in range(len(ACADEMIC_SLOTS))
            if (d, s) not in grid and not _in_reserved(d, s)
        ]
        random.shuffle(all_free)
        for d, s in all_free:
            if not theory_pool:
                break
            start_time = ACADEMIC_SLOTS[s][0]
            for i, cand in enumerate(theory_pool):
                s_key = (d, cand.id)
                if subject_daily_counts.get(s_key, 0) >= 3:
                    continue
                if check_single_conflict(
                    cand.teacher_name, d, start_time, class_key, grid
                ):
                    continue
                grid[(d, s)] = {"type": "TH", "subject": cand, "batch": "ALL"}
                subject_daily_counts[s_key] = subject_daily_counts.get(s_key, 0) + 1
                theory_pool.pop(i)
                break

    # ──────────────────────────────────────────────────────────────────────────
    # PRACTICAL BACKFILL — fill reserved pairs with remaining sessions
    # ──────────────────────────────────────────────────────────────────────────
    if remaining_sessions and reserved_pairs:
        reserved_slot_list = [
            (day, s1, s2)
            for day in days_list
            for s1, s2 in ADJACENT_PAIRS
            if (day, s1) in reserved_pairs
        ]
        random.shuffle(reserved_slot_list)

        for day, s1, s2 in reserved_slot_list:
            if not remaining_sessions:
                break
            if (day, s1) in grid or (day, s2) in grid:
                continue

            st1 = ACADEMIC_SLOTS[s1][0]
            st2 = ACADEMIC_SLOTS[s2][0]

            placed = False
            for idx, session in enumerate(remaining_sessions):
                subj_A1, subj_A2, subj_A3 = session
                teachers = list(
                    dict.fromkeys(
                        t
                        for t in [
                            subj_A1.teacher_name,
                            subj_A2.teacher_name,
                            subj_A3.teacher_name,
                        ]
                        if t != "-"
                    )
                )
                if check_teacher_conflict_bulk(teachers, day, st1, class_key, grid):
                    continue
                if check_teacher_conflict_bulk(teachers, day, st2, class_key, grid):
                    continue
                trio = [subj_A1, subj_A2, subj_A3]
                grid[(day, s1)] = {"type": "PR", "trio": trio}
                grid[(day, s2)] = {"type": "PR", "trio": trio}
                remaining_sessions.pop(idx)
                placed = True
                break

            # If teacher conflict prevents EVERY session here, put Library
            # so the slot is not left empty in the output
            if not placed:
                grid[(day, s1)] = {
                    "type": "FILLER",
                    "subject_name": "Library",
                    "batch": "ALL",
                }
                grid[(day, s2)] = {
                    "type": "FILLER",
                    "subject_name": "Library",
                    "batch": "ALL",
                }

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 4 — EXTRA / FILLER  (only if allow_extra=True)
    # ──────────────────────────────────────────────────────────────────────────
    if allow_extra:
        extra_counts = {inp.id: 0 for inp in all_inputs}
        final_gaps = [
            (d, s)
            for d in days_list
            for s in range(len(ACADEMIC_SLOTS))
            if (d, s) not in grid
        ]
        random.shuffle(final_gaps)

        for day, slot_idx in final_gaps:
            if (day, slot_idx) in grid:
                continue
            start_time = ACADEMIC_SLOTS[slot_idx][0]
            candidates = sorted(all_inputs, key=lambda x: extra_counts[x.id])
            placed_extra = None
            for cand in candidates:
                if not check_single_conflict(
                    cand.teacher_name, day, start_time, class_key, grid
                ):
                    placed_extra = cand
                    break
            if placed_extra:
                grid[(day, slot_idx)] = {
                    "type": "EXTRA",
                    "subject": placed_extra,
                    "batch": "ALL",
                }
                extra_counts[placed_extra.id] += 1
            else:
                grid[(day, slot_idx)] = {
                    "type": "FILLER",
                    "subject_name": "Library",
                    "batch": "ALL",
                }

    # ──────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ──────────────────────────────────────────────────────────────────────────
    for (day, slot_idx), data in grid.items():
        start, end = ACADEMIC_SLOTS[slot_idx]
        dtype = data["type"]

        if dtype in ("TH", "EXTRA"):
            subj = data["subject"]
            base_name = get_abbr(subj.subject_name)
            s_name = f"{base_name} - E" if dtype == "EXTRA" else base_name
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name=s_name,
                teacher_name=normalize_teacher_name(subj.teacher_name),
                batch="ALL",
            )

        elif dtype == "PR":
            trio_labs = data["trio"]
            for idx, batch_code in enumerate(("A1", "A2", "A3")):
                if idx < len(trio_labs):
                    lab_obj = trio_labs[idx]
                    s_name = get_abbr(lab_obj.subject_name)
                    t_name = normalize_teacher_name(lab_obj.teacher_name)
                else:
                    s_name, t_name = "Free", "-"
                TimetableModel.objects.create(
                    day=day,
                    start_time=start,
                    end_time=end,
                    subject_name=s_name,
                    teacher_name=t_name,
                    batch=batch_code,
                )

        elif dtype == "FILLER":
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name="Library",
                teacher_name="-",
                batch="ALL",
            )

    return True, "Generated"
    if class_key not in CLASS_CONFIG:
        return False, "Invalid Class"

    InputModel = CLASS_CONFIG[class_key]["input"]
    TimetableModel = CLASS_CONFIG[class_key]["timetable"]

    TimetableModel.objects.all().delete()

    all_inputs = list(InputModel.objects.all())
    for inp in all_inputs:
        inp.teacher_name = normalize_teacher_name(inp.teacher_name)

    days_list = [d[0] for d in DAYS]
    grid = {}  # (day, slot_index) -> data dict

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 1 — PRACTICALS
    # ──────────────────────────────────────────────────────────────────────────
    # Build per-batch pools with UNIQUE subject assignment per batch.
    # Subjects are distributed round-robin so each batch gets a different subject,
    # guaranteeing no two batches share the same teacher in a practical block.
    # e.g. A1 → STE, A2 → OSY, A3 → CLC (for a 3-subject practical slot)
    lab_pools = {"A1": [], "A2": [], "A3": []}
    batches = ["A1", "A2", "A3"]
    practical_subjects = [inp for inp in all_inputs if inp.practical_credits > 0]
    # Assign each practical subject exclusively to one batch (round-robin by subject index)
    for subj_idx, inp in enumerate(practical_subjects):
        assigned_batch = batches[subj_idx % 3]
        blocks_needed = inp.practical_credits // 2
        for _ in range(blocks_needed):
            lab_pools[assigned_batch].append(inp)

    for b in lab_pools:
        random.shuffle(lab_pools[b])

    # Build list of all (day, adjacent_pair) candidates — no 1-per-day limit.
    all_pr_candidates = []
    for day in days_list:
        for s1, s2 in ADJACENT_PAIRS:
            all_pr_candidates.append((day, s1, s2))
    random.shuffle(all_pr_candidates)

    def _try_place_trio(day, s1, s2, p1, p2, p3):
        """Try every combination of subjects from three lists; return winning trio or None."""
        st1 = ACADEMIC_SLOTS[s1][0]
        st2 = ACADEMIC_SLOTS[s2][0]
        cands = list(itertools.product(p1, p2, p3))
        random.shuffle(cands)
        for c1, c2, c3 in cands:
            # Subjects must differ across batches (no two batches doing same subject)
            if len({c1.id, c2.id, c3.id}) < 3:
                continue
            teachers = list(
                dict.fromkeys([c1.teacher_name, c2.teacher_name, c3.teacher_name])
            )
            if check_teacher_conflict_bulk(teachers, day, st1, class_key, grid):
                continue
            if check_teacher_conflict_bulk(teachers, day, st2, class_key, grid):
                continue
            return [c1, c2, c3]
        return None

    def _place_pr_blocks():
        """Consume lab_pools until all three are empty (not just when ALL three have items)."""
        for day, s1, s2 in all_pr_candidates:
            # Stop when every pool is empty
            if not any(lab_pools[b] for b in ("A1", "A2", "A3")):
                break
            if (day, s1) in grid or (day, s2) in grid:
                continue

            # We can skip this slot if no pool has items
            non_empty = [b for b in ("A1", "A2", "A3") if lab_pools[b]]
            if not non_empty:
                break

            # Attempt a full trio (all three batches have pending work)
            if lab_pools["A1"] and lab_pools["A2"] and lab_pools["A3"]:
                trio = _try_place_trio(
                    day, s1, s2, lab_pools["A1"], lab_pools["A2"], lab_pools["A3"]
                )
                if trio:
                    _commit_trio(day, s1, s2, trio)
                    continue

            # Partial trio — at least one batch pool has leftover items; pad others with
            # a Library placeholder so the slot is still useful for non-empty batches.
            class _Lib:
                subject_name = "Library"
                teacher_name = "-"
                id = -1

            padded = [
                lab_pools[b][0] if lab_pools[b] else _Lib() for b in ("A1", "A2", "A3")
            ]

            st1 = ACADEMIC_SLOTS[s1][0]
            st2 = ACADEMIC_SLOTS[s2][0]
            real = [x for x in padded if x.id != -1]
            if not real:
                continue
            teachers = list(
                dict.fromkeys(x.teacher_name for x in real if x.teacher_name != "-")
            )
            if check_teacher_conflict_bulk(teachers, day, st1, class_key, grid):
                continue
            if check_teacher_conflict_bulk(teachers, day, st2, class_key, grid):
                continue
            _commit_trio(day, s1, s2, padded)

    def _commit_trio(day, s1, s2, trio):
        grid[(day, s1)] = {"type": "PR", "trio": trio, "batches": ["A1", "A2", "A3"]}
        grid[(day, s2)] = {"type": "PR", "trio": trio, "batches": ["A1", "A2", "A3"]}
        for idx, b in enumerate(("A1", "A2", "A3")):
            lab = trio[idx]
            if lab.id != -1 and lab in lab_pools[b]:
                lab_pools[b].remove(lab)

    _place_pr_blocks()

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2 — THEORY  (fills all remaining free slots)
    # ──────────────────────────────────────────────────────────────────────────
    theory_pool = []
    for inp in all_inputs:
        for _ in range(inp.theory_credits):
            theory_pool.append(inp)
    random.shuffle(theory_pool)

    subject_daily_counts = {}

    # First pass: max 2 same-subject per day
    for day in days_list:
        free_slots = [i for i in range(len(ACADEMIC_SLOTS)) if (day, i) not in grid]
        random.shuffle(free_slots)
        for slot_idx in free_slots:
            if not theory_pool:
                break
            start_time = ACADEMIC_SLOTS[slot_idx][0]
            idxs = list(range(len(theory_pool)))
            random.shuffle(idxs)
            for i in idxs:
                cand = theory_pool[i]
                if check_single_conflict(
                    cand.teacher_name, day, start_time, class_key, grid
                ):
                    continue
                s_key = (day, cand.id)
                if subject_daily_counts.get(s_key, 0) >= 2:
                    continue
                grid[(day, slot_idx)] = {"type": "TH", "subject": cand, "batch": "ALL"}
                subject_daily_counts[s_key] = subject_daily_counts.get(s_key, 0) + 1
                theory_pool.pop(i)
                break

    # Backfill: relax daily cap to 3 for any remaining theory tasks
    if theory_pool:
        all_free = [
            (d, s)
            for d in days_list
            for s in range(len(ACADEMIC_SLOTS))
            if (d, s) not in grid
        ]
        random.shuffle(all_free)
        for d, s in all_free:
            if not theory_pool:
                break
            start_time = ACADEMIC_SLOTS[s][0]
            for i, cand in enumerate(theory_pool):
                s_key = (d, cand.id)
                if subject_daily_counts.get(s_key, 0) >= 3:
                    continue
                if check_single_conflict(
                    cand.teacher_name, d, start_time, class_key, grid
                ):
                    continue
                grid[(d, s)] = {"type": "TH", "subject": cand, "batch": "ALL"}
                subject_daily_counts[s_key] = subject_daily_counts.get(s_key, 0) + 1
                theory_pool.pop(i)
                break

    # Phase 2.5 backfill removed — practical deficit is handled post-persist
    # by fill_practical_deficit_for_class() called at the end.

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 3 — EXTRA / FILLER  (only if allow_extra=True)
    # ──────────────────────────────────────────────────────────────────────────
    if allow_extra:
        extra_counts = {inp.id: 0 for inp in all_inputs}
        final_gaps = [
            (d, s)
            for d in days_list
            for s in range(len(ACADEMIC_SLOTS))
            if (d, s) not in grid
        ]
        random.shuffle(final_gaps)

        for day, slot_idx in final_gaps:
            if (day, slot_idx) in grid:
                continue
            start_time = ACADEMIC_SLOTS[slot_idx][0]
            # Pick the least-used subject that doesn't conflict
            candidates = sorted(all_inputs, key=lambda x: extra_counts[x.id])
            placed_extra = None
            for cand in candidates:
                if not check_single_conflict(
                    cand.teacher_name, day, start_time, class_key, grid
                ):
                    placed_extra = cand
                    break
            if placed_extra:
                grid[(day, slot_idx)] = {
                    "type": "EXTRA",
                    "subject": placed_extra,
                    "batch": "ALL",
                }
                extra_counts[placed_extra.id] += 1
            else:
                grid[(day, slot_idx)] = {
                    "type": "FILLER",
                    "subject_name": "Library",
                    "batch": "ALL",
                }

    # ──────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ──────────────────────────────────────────────────────────────────────────
    for (day, slot_idx), data in grid.items():
        start, end = ACADEMIC_SLOTS[slot_idx]
        dtype = data["type"]

        if dtype in ("TH", "EXTRA"):
            subj = data["subject"]
            base_name = get_abbr(subj.subject_name)
            s_name = f"{base_name} - E" if dtype == "EXTRA" else base_name
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name=s_name,
                teacher_name=normalize_teacher_name(subj.teacher_name),
                batch="ALL",
            )

        elif dtype == "PR":
            trio_labs = data["trio"]
            for idx, batch_code in enumerate(("A1", "A2", "A3")):
                if idx < len(trio_labs):
                    lab_obj = trio_labs[idx]
                    s_name = get_abbr(lab_obj.subject_name)
                    t_name = normalize_teacher_name(lab_obj.teacher_name)
                else:
                    s_name, t_name = "Free", "-"
                TimetableModel.objects.create(
                    day=day,
                    start_time=start,
                    end_time=end,
                    subject_name=s_name,
                    teacher_name=t_name,
                    batch=batch_code,
                )

        elif dtype == "FILLER":
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name="Library",
                teacher_name="-",
                batch="ALL",
            )

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 4 — DB-LEVEL PRACTICAL DEFICIT FILL
    # Now that everything is persisted, run the dedicated practical filler.
    # It works on actual DB rows and can displace Library/Filler placeholders.
    # ──────────────────────────────────────────────────────────────────────────
    fill_practical_deficit_for_class(class_key)

    return True, "Generated"


# ──────────────────────────────────────────────────────────────────────────────
# DEDICATED PRACTICAL DEFICIT FILLER
# Works on the persisted timetable (DB rows). Called at the end of generation
# and can also be triggered standalone. Displaces Library/Filler slots to place
# practical blocks wherever there is a deficit.
# ──────────────────────────────────────────────────────────────────────────────


def fill_practical_deficit_for_class(class_key):
    """
    Scans the generated timetable for practical deficits, finds available
    adjacent-pair slots (free OR Library/Filler), and fills them with the
    missing practical workload.

    Strategy per batch:
      1. Compute how many 2-hr practical blocks are still needed per (subject, batch).
      2. Collect candidate adjacent slot pairs that are free or displace-able.
      3. For each candidate pair, build a valid trio (A1, A2, A3) where each
         batch's subject is unique. Batches with no deficit get Library.
      4. Write the practical rows into DB, removing any displaced Library rows.
    """
    if class_key not in CLASS_CONFIG:
        return

    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg["input"]
    TimetableModel = cfg["timetable"]

    all_inputs = list(InputModel.objects.all())
    for inp in all_inputs:
        inp.teacher_name = normalize_teacher_name(inp.teacher_name)

    days_list = [d[0] for d in DAYS]

    # ── Step 1: compute how many practical blocks are placed per (subject, batch) ──
    def _placed_blocks(inp, batch):
        """
        Count 2-hr practical blocks already in DB for this subject+batch.
        We count unique (day, start_time) pairs where start_time is a pair-start.
        """
        pair_starts = {ACADEMIC_SLOTS[s1][0] for s1, _ in ADJACENT_PAIRS}
        rows = (
            TimetableModel.objects.filter(
                subject_name=get_abbr(inp.subject_name),
                batch=batch,
                start_time__in=pair_starts,
            )
            .values_list("day", "start_time")
            .distinct()
        )
        return len(set(rows))

    # Build deficit map: {batch: [(subject, blocks_needed), ...]}
    deficit_map = {"A1": [], "A2": [], "A3": []}
    for inp in all_inputs:
        if inp.practical_credits <= 0:
            continue
        expected = inp.practical_credits // 2
        for batch in ("A1", "A2", "A3"):
            placed = _placed_blocks(inp, batch)
            if placed < expected:
                deficit_map[batch].append((inp, expected - placed))

    if not any(deficit_map[b] for b in ("A1", "A2", "A3")):
        return  # Nothing to do

    # ── Step 2: find candidate adjacent pairs ──
    # Priority: fully free pairs first, then pairs that only have Library/Filler.
    def _is_displaceable(day, start_time, end_time):
        """True if the slot only has Library or Filler records (safe to replace)."""
        rows = TimetableModel.objects.filter(day=day, start_time=start_time)
        if not rows.exists():
            return True  # completely free
        return all(r.subject_name in ("Library", "Free") for r in rows)

    candidate_pairs = []
    for day in days_list:
        for s1, s2 in ADJACENT_PAIRS:
            st1, et1 = ACADEMIC_SLOTS[s1]
            st2, et2 = ACADEMIC_SLOTS[s2]
            if _is_displaceable(day, st1, et1) and _is_displaceable(day, st2, et2):
                # Check no practical already occupies this pair for ANY batch
                if (
                    not TimetableModel.objects.filter(
                        day=day, start_time=st1, batch__in=("A1", "A2", "A3")
                    )
                    .exclude(subject_name__in=("Library", "Free"))
                    .exists()
                ):
                    candidate_pairs.append((day, s1, s2))

    random.shuffle(candidate_pairs)

    # ── Step 3 & 4: fill deficit practical blocks ──
    class _Lib:
        subject_name = "Library"
        teacher_name = "-"
        id = -1

    batch_order = ("A1", "A2", "A3")

    for day, s1, s2 in candidate_pairs:
        # Rebuild deficit lists each iteration (counts may have changed)
        remaining = {b: [inp for inp, _ in deficit_map[b]] for b in batch_order}
        if not any(remaining[b] for b in batch_order):
            break

        st1, et1 = ACADEMIC_SLOTS[s1]
        st2, et2 = ACADEMIC_SLOTS[s2]

        # Pick one subject per batch (the first available in deficit list)
        trio_subjs = []
        for batch in batch_order:
            if remaining[batch]:
                trio_subjs.append(remaining[batch][0])
            else:
                trio_subjs.append(_Lib())

        # Enforce uniqueness: all real (non-Library) subjects must differ
        real = [x for x in trio_subjs if x.id != -1]
        real_ids = [x.id for x in real]
        if len(real_ids) != len(set(real_ids)):
            continue  # duplicate subjects — skip this pair

        # Teacher conflict check against other classes
        teachers = list(
            dict.fromkeys(x.teacher_name for x in real if x.teacher_name != "-")
        )
        if check_teacher_conflict_bulk(teachers, day, st1, class_key, None):
            continue
        if check_teacher_conflict_bulk(teachers, day, st2, class_key, None):
            continue

        # Displace any existing Library/Filler rows in both slots
        TimetableModel.objects.filter(day=day, start_time__in=[st1, st2]).delete()

        # Write PR rows for each slot in the pair
        for slot_start, slot_end in [(st1, et1), (st2, et2)]:
            for idx, batch in enumerate(batch_order):
                subj = trio_subjs[idx]
                TimetableModel.objects.create(
                    day=day,
                    start_time=slot_start,
                    end_time=slot_end,
                    subject_name=get_abbr(subj.subject_name),
                    teacher_name=normalize_teacher_name(subj.teacher_name),
                    batch=batch,
                )

        # Decrement deficit counts
        for idx, batch in enumerate(batch_order):
            subj = trio_subjs[idx]
            if subj.id != -1:
                deficit_map[batch] = [
                    (inp, cnt - 1) if inp.id == subj.id else (inp, cnt)
                    for inp, cnt in deficit_map[batch]
                ]
                deficit_map[batch] = [
                    (inp, cnt) for inp, cnt in deficit_map[batch] if cnt > 0
                ]


# ──────────────────────────────────────────────────────────────────────────────
# VALIDATION & ANALYTICS  (unchanged logic, kept for views.py compatibility)
# ──────────────────────────────────────────────────────────────────────────────


def validate_workload_distribution(class_key):
    """Comprehensive validation of practical and theory workload distribution."""
    if class_key not in CLASS_CONFIG:
        return {"error": "Invalid Class"}

    from datetime import datetime

    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg["timetable"]
    InputModel = cfg["input"]

    validation = {
        "theory_distribution": [],
        "practical_distribution": [],
        "theory_balanced": True,
        "practical_balanced": True,
        "total_theory_deficit": 0,
        "total_practical_deficit": 0,
        "recommendations": [],
    }

    inputs = InputModel.objects.all()

    for inp in inputs:
        exp_theory = inp.theory_credits
        abbr = get_abbr(inp.subject_name)

        actual_theory = (
            TimetableModel.objects.filter(subject_name=abbr, batch="ALL")
            .exclude(subject_name__contains=" - E")
            .count()
        )
        extra_theory = TimetableModel.objects.filter(
            subject_name__contains=f"{abbr} - E", batch="ALL"
        ).count()

        theory_status = "OK"
        if actual_theory < exp_theory:
            deficit = exp_theory - actual_theory
            theory_status = f"DEFICIT: {deficit} sessions"
            validation["theory_balanced"] = False
            validation["total_theory_deficit"] += deficit
            validation["recommendations"].append(
                f"Add {deficit} more theory session(s) for {inp.subject_name}"
            )
        elif actual_theory > exp_theory:
            excess = actual_theory - exp_theory
            theory_status = f"EXCESS: {excess} sessions"

        validation["theory_distribution"].append(
            {
                "subject": inp.subject_name,
                "teacher": inp.teacher_name,
                "expected": exp_theory,
                "actual": actual_theory,
                "extra": extra_theory,
                "status": theory_status,
            }
        )

        if inp.practical_credits > 0:
            exp_practical_blocks = inp.practical_credits // 2

            for batch in ("A1", "A2", "A3"):
                practical_entries = TimetableModel.objects.filter(
                    subject_name=abbr, batch=batch
                ).order_by("day", "start_time")

                # Count 2-hour blocks (consecutive pairs)
                actual_blocks = 0
                prev_entry = None
                for entry in practical_entries:
                    if prev_entry:
                        time_diff = (
                            datetime.combine(datetime.today(), entry.start_time)
                            - datetime.combine(datetime.today(), prev_entry.end_time)
                        ).seconds
                        if time_diff <= 900:
                            actual_blocks += 1
                            prev_entry = None
                            continue
                    prev_entry = entry

                if len(practical_entries) % 2 == 1:
                    actual_blocks += 0.5

                practical_status = "OK"
                if actual_blocks < exp_practical_blocks:
                    deficit = exp_practical_blocks - actual_blocks
                    practical_status = f"DEFICIT: {deficit} blocks"
                    validation["practical_balanced"] = False
                    validation["total_practical_deficit"] += deficit
                    validation["recommendations"].append(
                        f"Add {deficit} practical block(s) for {inp.subject_name} - Batch {batch}"
                    )
                elif actual_blocks > exp_practical_blocks:
                    excess = actual_blocks - exp_practical_blocks
                    practical_status = f"EXCESS: {excess} blocks"

                validation["practical_distribution"].append(
                    {
                        "subject": inp.subject_name,
                        "teacher": inp.teacher_name,
                        "batch": batch,
                        "expected_blocks": exp_practical_blocks,
                        "actual_blocks": actual_blocks,
                        "status": practical_status,
                    }
                )

    if validation["theory_balanced"] and validation["practical_balanced"]:
        validation["overall_status"] = "BALANCED"
    elif not validation["theory_balanced"] and not validation["practical_balanced"]:
        validation["overall_status"] = (
            "CRITICAL: Both theory and practical workload unbalanced"
        )
    elif not validation["theory_balanced"]:
        validation["overall_status"] = "WARNING: Theory workload unbalanced"
    else:
        validation["overall_status"] = "WARNING: Practical workload unbalanced"

    return validation


def analyze_timetable(class_key):
    """Analyzes the generated timetable for conflicts and workload distribution."""
    if class_key not in CLASS_CONFIG:
        return {"error": "Invalid Class"}

    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg["timetable"]
    InputModel = cfg["input"]

    analysis = {
        "conflicts": [],
        "distribution": [],
        "is_balanced": True,
        "has_conflicts": False,
    }

    my_entries = TimetableModel.objects.all()

    for entry in my_entries:
        if entry.teacher_name in ("-", "Free"):
            continue
        for other_key, other_cfg in CLASS_CONFIG.items():
            if other_key == class_key:
                continue
            OtherTimetable = other_cfg["timetable"]
            overlaps = OtherTimetable.objects.filter(
                teacher_name=entry.teacher_name,
                day=entry.day,
                start_time=entry.start_time,
            )
            for overlap in overlaps:
                analysis["conflicts"].append(
                    {
                        "teacher": entry.teacher_name,
                        "day": entry.day,
                        "time": f"{entry.start_time} - {entry.end_time}",
                        "other_class": other_cfg["name"],
                        "other_subject": overlap.subject_name,
                    }
                )
                analysis["has_conflicts"] = True

    inputs = InputModel.objects.all()
    for inp in inputs:
        exp_th = inp.theory_credits
        exp_pr = inp.practical_credits
        abbr = get_abbr(inp.subject_name)

        act_th = TimetableModel.objects.filter(
            subject_name__startswith=abbr, batch="ALL"
        ).count()

        status = "Balanced"
        if act_th < exp_th:
            status = "Underloaded (Theory)"
            analysis["is_balanced"] = False
        elif act_th > (exp_th + 2):
            status = "Overloaded (Theory)"

        batches = ("A1", "A2", "A3")
        pr_status = []
        for b in batches:
            b_act = TimetableModel.objects.filter(subject_name=abbr, batch=b).count()
            exp_per_batch = exp_pr  # expected total rows per batch
            if b_act < exp_per_batch:
                pr_status.append(f"{b}: Low ({b_act}/{exp_per_batch})")
                analysis["is_balanced"] = False
            elif b_act > exp_per_batch:
                pr_status.append(f"{b}: High ({b_act}/{exp_per_batch})")

        analysis["distribution"].append(
            {
                "subject": inp.subject_name,
                "teacher": inp.teacher_name,
                "expected_th": exp_th,
                "actual_th": act_th,
                "expected_pr": exp_pr,
                "practical_status": ", ".join(pr_status) if pr_status else "OK",
                "status": status,
            }
        )

    return analysis


# ──────────────────────────────────────────────────────────────────────────────
# STANDALONE helpers called by add_extra_lectures_view
# ──────────────────────────────────────────────────────────────────────────────


def fill_extra_lectures_for_class(class_key):
    """
    Fill any remaining empty (non-break) slots in an already-generated
    timetable with extra lectures.  Does NOT clear or regenerate the timetable.
    """
    if class_key not in CLASS_CONFIG:
        return

    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg["input"]
    TimetableModel = cfg["timetable"]

    all_inputs = list(InputModel.objects.all())
    days_list = [d[0] for d in DAYS]

    # Build a set of already-occupied (day, start_time) keys
    occupied = set(TimetableModel.objects.values_list("day", "start_time"))

    extra_counts = {inp.id: 0 for inp in all_inputs}
    candidates = [
        (day, start, end)
        for day in days_list
        for start, end in ACADEMIC_SLOTS
        if (day, start) not in occupied
    ]
    random.shuffle(candidates)

    for day, start, end in candidates:
        sorted_inputs = sorted(all_inputs, key=lambda x: extra_counts[x.id])
        placed = None
        for cand in sorted_inputs:
            # Simple conflict check against other classes only; within-class is excluded
            conflict = any(
                cfg2["timetable"]
                .objects.filter(
                    teacher_name=normalize_teacher_name(cand.teacher_name),
                    day=day,
                    start_time=start,
                )
                .exists()
                for key2, cfg2 in CLASS_CONFIG.items()
                if key2 != class_key
            )
            if not conflict:
                placed = cand
                break
        if placed:
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name=f"{get_abbr(placed.subject_name)} - E",
                teacher_name=normalize_teacher_name(placed.teacher_name),
                batch="ALL",
            )
            extra_counts[placed.id] += 1
        else:
            TimetableModel.objects.create(
                day=day,
                start_time=start,
                end_time=end,
                subject_name="Library",
                teacher_name="-",
                batch="ALL",
            )
