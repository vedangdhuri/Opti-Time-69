with open("class_timetable_v2/utils.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

try:
    start_pr = lines.index("    # --- STEP A: SCHEDULE PRACTICALS ---\n")
    start_th = lines.index("    # --- STEP B: SCHEDULE THEORY ---\n")
    end_th = lines.index("    # --- STEP C: FILL GAPS WITH EXTRA LECTURES ---\n")
except ValueError as e:
    print(f"Failed to find indices: {e}")
    import sys
    sys.exit(1)

new_lines = lines[:start_pr]
new_lines.append("    run_order = ['PR', 'TH'] if class_key == 'fyco' else ['TH', 'PR']\n")
new_lines.append("    for current_phase in run_order:\n")
new_lines.append("        if current_phase == 'PR':\n")

for i in range(start_pr, start_th):
    if lines[i].strip() == "":
        new_lines.append(lines[i])
    else:
        new_lines.append("        " + lines[i])

new_lines.append("        elif current_phase == 'TH':\n")
for i in range(start_th, end_th):
    if lines[i].strip() == "":
        new_lines.append(lines[i])
    else:
        new_lines.append("        " + lines[i])

new_lines.extend(lines[end_th:])

with open("class_timetable_v2/utils.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("class_timetable_v2 fixed")
