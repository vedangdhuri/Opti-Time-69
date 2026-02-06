from ortools.sat.python import cp_model

def generate_simple_timetable(classes, subjects, rooms, slots):
    model = cp_model.CpModel()
    x = {}

    for c in classes:
        for s in subjects:
            for r in rooms:
                for t in slots:
                    x[(c.id, s.id, r.id, t.id)] = model.NewBoolVar(
                        f"x_{c.id}_{s.id}_{r.id}_{t.id}"
                    )

    # Weekly hours per subject (CRITICAL FIX)
    for c in classes:
        for s in subjects:
            model.Add(
                sum(
                    x[(c.id, s.id, r.id, t.id)]
                    for r in rooms for t in slots
                ) == s.weekly_hours
            )

    # Room overlap
    for r in rooms:
        for t in slots:
            model.Add(
                sum(
                    x[(c.id, s.id, r.id, t.id)]
                    for c in classes for s in subjects
                ) <= 1
            )

    # Spread same subject across days (no repeat same day)
    for c in classes:
        for s in subjects:
            for day in set(t.day for t in slots):
                model.Add(
                    sum(
                        x[(c.id, s.id, r.id, t.id)]
                        for r in rooms
                        for t in slots
                        if t.day == day
                    ) <= 1
                )

    # Prefer early slots
    model.Minimize(
        sum(
            t.slot * x[(c.id, s.id, r.id, t.id)]
            for c in classes
            for s in subjects
            for r in rooms
            for t in slots
        )
    )

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    return [key for key, var in x.items() if solver.Value(var)]
