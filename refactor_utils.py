with open("class_timetable/utils.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

try:
    start_th = lines.index("    # --- STEP B: SCHEDULE THEORY (MOVED TO TOP) ---\n")
    start_pr = lines.index("    # --- STEP A: SCHEDULE PRACTICALS ---\n")
    end_pr = lines.index("    # --- STEP D: FILL REMAINING GAPS WITH EXTRA LECTURES ---\n")
except ValueError as e:
    print(f"Failed to find indices: {e}")
    sys.exit(1)

new_lines = lines[:start_th]
new_lines.append("    run_order = ['PR', 'TH'] if class_key == 'fyco' else ['TH', 'PR']\n")
new_lines.append("    for current_phase in run_order:\n")
new_lines.append("        if current_phase == 'TH':\n")

for i in range(start_th, start_pr):
    if lines[i].strip() == "":
        new_lines.append(lines[i])
    else:
        # The original code has 4 spaces of indentation.
        # We need it to be at 12 spaces (inside `for` (4) -> `if` (8) -> code (12))
        # Wait: The original code starts with 4 spaces. We want to ADD 8 spaces.
        new_lines.append("        " + lines[i])

new_lines.append("        elif current_phase == 'PR':\n")
for i in range(start_pr, end_pr):
    if lines[i].strip() == "":
        new_lines.append(lines[i])
    else:
        new_lines.append("        " + lines[i])

new_lines.extend(lines[end_pr:])

with open("class_timetable/utils.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("class_timetable fixed")
