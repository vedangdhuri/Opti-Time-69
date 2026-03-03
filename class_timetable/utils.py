import random
import itertools
from datetime import time, datetime, timedelta
from .models import (
    TycoInput,
    TycoTimetable,
    SycoInput,
    SycoTimetable,
    FycoInput,
    FycoTimetable,
    DAYS,
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
    "tyco": {"input": TycoInput, "timetable": TycoTimetable, "name": "TYCO"},
    "syco": {"input": SycoInput, "timetable": SycoTimetable, "name": "SYCO"},
    "fyco": {"input": FycoInput, "timetable": FycoTimetable, "name": "FYCO"},
}

# --- HELPER FOR ABBREVIATIONS ---
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
    "ENTREPRENEURSHIP DEVELOPMENT AND STARTUPS": "ENDS",
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
    "Professional Communication": "POC",
    "Applied Mathematics": "AMS",
}


def get_abbr(name):
    return SUBJECT_ABBR.get(name, name[:3].upper())


def normalize_teacher_name(name):
    """Strip and collapse internal whitespace so 'P.D. Kate' == 'P.D.Kate' during matching."""
    return " ".join(str(name).strip().split())


def _teachers_in_grid_at(grid, day, start_time):
    """Return the set of normalized teacher names already in the in-memory grid at (day, start_time)."""
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
    """
    Returns True if ANY teacher in the list is busy:
      - in another class's DB timetable at the same day/time, OR
      - in the current class's in-memory grid at the same day/time.
    Teacher names are normalized (whitespace-collapsed) before comparison.
    """
    from django.db.models.functions import Trim

    normalized = [normalize_teacher_name(n) for n in teacher_list]
    normalized_set = set(normalized)

    # 1. Cross-class DB check (with SQL TRIM so whitespace differences don't cause misses)
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

    # 2. Within-class in-memory grid check
    if current_grid is not None:
        grid_teachers = _teachers_in_grid_at(current_grid, day, start_time)
        if normalized_set & grid_teachers:  # any overlap
            return True

    return False


def check_single_conflict(
    teacher, day, start_time, exclude_class_key, current_grid=None
):
    return check_teacher_conflict_bulk(
        [teacher], day, start_time, exclude_class_key, current_grid
    )


def generate_timetable_for_class(class_key):
    """
    3-phase scheduling: PRACTICALS first, THEORY second, EXTRA last.
    Phase 2.5 runs an extra practical pass AFTER theory to exhaust
    any remaining deficit before filling gaps with extra lectures.
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
    grid = {}

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PHASE 1 â€“ PRACTICALS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    lab_pools = {"A1": [], "A2": [], "A3": []}
    for inp in all_inputs:
        blocks_needed = inp.practical_credits // 2
        for _ in range(blocks_needed):
            for batch in ["A1", "A2", "A3"]:
                lab_pools[batch].append(inp)

    for b in lab_pools:
        random.shuffle(lab_pools[b])

    # All strictly-adjacent 2-hour slot pairs across the whole week
    all_pr_slots = []
    for day in days_list:
        for ss in range(len(ACADEMIC_SLOTS) - 1):
            if ACADEMIC_SLOTS[ss][1] == ACADEMIC_SLOTS[ss + 1][0]:
                all_pr_slots.append((day, ss))
    random.shuffle(all_pr_slots)

    def _place_pr_trio(day, s1, s2, p1_list, p2_list, p3_list):
        """Try to find a valid trio from three batch pools and return it, or None."""
        st1 = ACADEMIC_SLOTS[s1][0]
        st2 = ACADEMIC_SLOTS[s2][0]
        cands = list(itertools.product(p1_list, p2_list, p3_list))
        random.shuffle(cands)
        for c1, c2, c3 in cands:
            # All 3 subjects must be different
            if len({c1.id, c2.id, c3.id}) < 3:
                continue
            unique_t = list(
                dict.fromkeys([c1.teacher_name, c2.teacher_name, c3.teacher_name])
            )
            if check_teacher_conflict_bulk(unique_t, day, st1, class_key, grid):
                continue
            if check_teacher_conflict_bulk(unique_t, day, st2, class_key, grid):
                continue
            return [c1, c2, c3]
        return None

    for day, ss in all_pr_slots:
        if not any(lab_pools[b] for b in ["A1", "A2", "A3"]):
            break
        s1, s2 = ss, ss + 1
        if (day, s1) in grid or (day, s2) in grid:
            continue
        if not (lab_pools["A1"] and lab_pools["A2"] and lab_pools["A3"]):
            continue
        trio = _place_pr_trio(
            day, s1, s2, lab_pools["A1"], lab_pools["A2"], lab_pools["A3"]
        )
        if trio:
            grid[(day, s1)] = {
                "type": "PR",
                "trio": trio,
                "batches": ["A1", "A2", "A3"],
            }
            grid[(day, s2)] = {
                "type": "PR",
                "trio": trio,
                "batches": ["A1", "A2", "A3"],
            }
            lab_pools["A1"].remove(trio[0])
            lab_pools["A2"].remove(trio[1])
            lab_pools["A3"].remove(trio[2])

    # Phase 1 backfill â€“ place remaining deficit into free pairs
    def _compute_pr_deficit():
        deficit = {}
        for inp in all_inputs:
            if inp.practical_credits <= 0:
                continue
            expected = inp.practical_credits // 2
            for bidx, bat in enumerate(["A1", "A2", "A3"]):
                placed = sum(
                    1
                    for (d, s), data in grid.items()
                    if data.get("type") == "PR"
                    and bidx < len(data.get("trio", []))
                    and data["trio"][bidx].id == inp.id
                )
                blocks = placed // 2
                if blocks < expected:
                    deficit[(inp.id, bat)] = {
                        "subject": inp,
                        "deficit": expected - blocks,
                        "bidx": bidx,
                    }
        return deficit

    def _backfill_practicals(deficit_dict):
        """Place remaining practical deficit into free adjacent pairs."""
        if not deficit_dict:
            return

        class _Lib:
            subject_name = "Library"
            teacher_name = "-"
            id = -1

        free_pairs = [
            (day, ss)
            for day in days_list
            for ss in range(len(ACADEMIC_SLOTS) - 1)
            if ACADEMIC_SLOTS[ss][1] == ACADEMIC_SLOTS[ss + 1][0]
            and (day, ss) not in grid
            and (day, ss + 1) not in grid
        ]
        random.shuffle(free_pairs)

        for day, ss in free_pairs:
            if not deficit_dict:
                break
            s1, s2 = ss, ss + 1
            if (day, s1) in grid or (day, s2) in grid:
                continue
            st1 = ACADEMIC_SLOTS[s1][0]
            st2 = ACADEMIC_SLOTS[s2][0]

            batch_cands = {"A1": [], "A2": [], "A3": []}
            for (iid, bat), info in deficit_dict.items():
                batch_cands[bat].append(info["subject"])

            def _valid(combo):
                real = [x for x in combo if x is not None]
                if not real:
                    return False
                real_ids = [x.id for x in real if x.id != -1]
                if len(real_ids) != len(set(real_ids)):
                    return False
                teachers = list(dict.fromkeys(x.teacher_name for x in real))
                return not check_teacher_conflict_bulk(
                    teachers, day, st1, class_key, grid
                ) and not check_teacher_conflict_bulk(
                    teachers, day, st2, class_key, grid
                )

            combo = None

            # Full trio
            if batch_cands["A1"] and batch_cands["A2"] and batch_cands["A3"]:
                opts = list(
                    itertools.product(
                        batch_cands["A1"], batch_cands["A2"], batch_cands["A3"]
                    )
                )
                random.shuffle(opts)
                for opt in opts:
                    if _valid(opt):
                        combo = list(opt)
                        break

            # Partial
            if not combo:
                for _ in range(80):
                    c1 = random.choice(batch_cands["A1"]) if batch_cands["A1"] else None
                    c2 = random.choice(batch_cands["A2"]) if batch_cands["A2"] else None
                    c3 = random.choice(batch_cands["A3"]) if batch_cands["A3"] else None
                    if not any([c1, c2, c3]):
                        continue
                    if _valid((c1, c2, c3)):
                        combo = [c1, c2, c3]
                        break

            if combo:
                safe = [x if x is not None else _Lib() for x in combo]
                grid[(day, s1)] = {
                    "type": "PR",
                    "trio": safe,
                    "batches": ["A1", "A2", "A3"],
                }
                grid[(day, s2)] = {
                    "type": "PR",
                    "trio": safe,
                    "batches": ["A1", "A2", "A3"],
                }
                for idx, bat in enumerate(["A1", "A2", "A3"]):
                    subj = safe[idx]
                    if subj.id != -1:
                        key = (subj.id, bat)
                        if key in deficit_dict:
                            deficit_dict[key]["deficit"] -= 1
                            if deficit_dict[key]["deficit"] <= 0:
                                del deficit_dict[key]

    _backfill_practicals(_compute_pr_deficit())

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PHASE 2 â€“ THEORY
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    theory_pool = []
    for inp in all_inputs:
        for _ in range(inp.theory_credits):
            theory_pool.append(inp)
    random.shuffle(theory_pool)

    subject_daily_counts = {}

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

    # Theory backfill (relax daily cap to 3)
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

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PHASE 2.5 â€“ PRACTICAL RE-DISTRIBUTION (post-theory pass)
    # After theory is placed, try one more time to fill remaining practical
    # deficit in whatever 2-hour adjacent pairs are still free.
    # Only after this is exhausted do extras go in.
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _backfill_practicals(_compute_pr_deficit())

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PHASE 3 â€“ EXTRA / FILLER
    # Fill any still-empty slots with extra lectures, distributed evenly.
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PERSIST TO DATABASE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            for idx, batch_code in enumerate(["A1", "A2", "A3"]):
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


def validate_workload_distribution(class_key):
    """
    Comprehensive validation of practical and theory workload distribution.
    Returns detailed report on what's missing and what needs to be redistributed.
    """
    if class_key not in CLASS_CONFIG:
        return {"error": "Invalid Class"}

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
        # === THEORY VALIDATION ===
        exp_theory = inp.theory_credits
        abbr = get_abbr(inp.subject_name)

        # Count actual theory sessions (excluding extras)
        actual_theory = (
            TimetableModel.objects.filter(subject_name=abbr, batch="ALL")
            .exclude(subject_name__contains=" - E")
            .count()
        )

        # Count extra sessions
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

        # === PRACTICAL VALIDATION (PER BATCH) ===
        if inp.practical_credits > 0:
            exp_practical_blocks = inp.practical_credits // 2

            for batch in ["A1", "A2", "A3"]:
                # Count practical sessions for this batch
                # Each practical block appears in 2 consecutive slots
                practical_entries = TimetableModel.objects.filter(
                    subject_name=abbr, batch=batch
                ).order_by("day", "start_time")

                # Count unique blocks (consecutive pairs)
                actual_blocks = 0
                prev_entry = None
                for entry in practical_entries:
                    if prev_entry:
                        # Check if this is consecutive with previous
                        time_diff = (
                            datetime.combine(datetime.today(), entry.start_time)
                            - datetime.combine(datetime.today(), prev_entry.end_time)
                        ).seconds
                        if (
                            time_diff <= 900
                        ):  # Within 15 minutes (accounting for breaks)
                            actual_blocks += 1
                            prev_entry = None
                            continue
                    prev_entry = entry

                # If odd number of entries, count the last one as a partial block
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

    # Overall assessment
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
    """
    Analyzes the generated timetable for conflicts and workload distribution.
    """
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

    # 1. Check Conflicts
    my_entries = TimetableModel.objects.all()

    for entry in my_entries:
        if entry.teacher_name in ["-", "Free"]:
            continue

        # Check against all other classes
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

    # 2. Check Workload Distribution
    inputs = InputModel.objects.all()

    for inp in inputs:
        exp_th = inp.theory_credits
        exp_pr = inp.practical_credits  # Total practical hours (credits)

        abbr = get_abbr(inp.subject_name)

        act_th = TimetableModel.objects.filter(
            subject_name__startswith=abbr, batch="ALL"
        ).count()

        # ACT PR: Sum of entries across all batches
        act_pr = TimetableModel.objects.filter(
            subject_name=abbr, batch__in=["A1", "A2", "A3"]
        ).count()

        status = "Balanced"
        if act_th < exp_th:
            status = "Underloaded (Theory)"
            analysis["is_balanced"] = False
        elif act_th > (exp_th + 2):
            status = "Overloaded (Theory)"

        # Check Practical Batch-wise
        batches = ["A1", "A2", "A3"]
        pr_status = []
        for b in batches:
            b_act = TimetableModel.objects.filter(subject_name=abbr, batch=b).count()
            if b_act < exp_pr:
                pr_status.append(f"{b}: Low ({b_act}/{exp_pr})")
                analysis["is_balanced"] = False
            elif b_act > exp_pr:
                pr_status.append(f"{b}: High ({b_act}/{exp_pr})")

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