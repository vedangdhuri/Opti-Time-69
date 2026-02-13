from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .utils import CLASS_CONFIG, generate_timetable_for_class, ACADEMIC_SLOTS
from .forms import TycoAInputForm, TycoBInputForm, SycoAInputForm, SycoBInputForm
from datetime import time

def dashboard(request):
    classes = CLASS_CONFIG.keys()
    context = {'classes': classes, 'class_config': CLASS_CONFIG}
    return render(request, 'class_timetable/dashboard.html', context)

def input_data(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect('class_timetable:dashboard')
    
    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg['input']
    
    form_map = {
        'tyco_a': TycoAInputForm,
        'tyco_b': TycoBInputForm,
        'syco_a': SycoAInputForm,
        'syco_b': SycoBInputForm,
    }
    FormClass = form_map.get(class_key)
    
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Input added for {cfg['name']}")
            return redirect('class_timetable:input_data', class_key=class_key)
    else:
        form = FormClass()

    existing_inputs = InputModel.objects.all()
    
    return render(request, 'class_timetable/input.html', {
        'class_key': class_key,
        'class_name': cfg['name'],
        'form': form,
        'inputs': existing_inputs
    })

def delete_input(request, class_key, input_id):
    if class_key not in CLASS_CONFIG:
        return redirect('class_timetable:dashboard')
        
    cfg = CLASS_CONFIG[class_key]
    InputModel = cfg['input']
    
    input_obj = get_object_or_404(InputModel, id=input_id)
    input_obj.delete()
    messages.success(request, f"Input deleted for {cfg['name']}")
    return redirect('class_timetable:input_data', class_key=class_key)

def generate_timetable_view(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect('class_timetable:dashboard')
        
    success, msg = generate_timetable_for_class(class_key)
    if success:
        messages.success(request, f"Timetable generated for {class_key}")
    else:
        messages.error(request, f"Error: {msg}")
        
    return redirect('class_timetable:view_timetable', class_key=class_key)

def view_timetable(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect('class_timetable:dashboard')
        
    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg['timetable']
    
    # Predefined Week Days in Order
    DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # 1. Build Slot List including Breaks for Display
    # Match ACADEMIC_SLOTS from utils + insert breaks
    
    def fmt(t): return t.strftime("%I:%M %p")

    # Define rows manually to match standard output structure
    view_rows = [
        {'start': time(10,0), 'end': time(11,0), 'label': '10:00 am to 11:00 am', 'type': 'slot'},
        {'start': time(11,0), 'end': time(12,0), 'label': '11:00 am to 12:00 pm', 'type': 'slot'},
        {'label': 'LUNCH BREAK', 'type': 'break', 'start': time(12,0), 'end': time(12,45)},
        {'start': time(12,45), 'end': time(13,45), 'label': '12:45 pm to 01:45 pm', 'type': 'slot'},
        {'start': time(13,45), 'end': time(14,45), 'label': '01:45 pm to 02:45 pm', 'type': 'slot'},
        {'label': 'TEA BREAK', 'type': 'break', 'start': time(14,45), 'end': time(15,0)},
        {'start': time(15,0), 'end': time(16,0), 'label': '03:00 pm to 04:00 pm', 'type': 'slot'},
        {'start': time(16,0), 'end': time(17,0), 'label': '04:00 pm to 05:00 pm', 'type': 'slot'},
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
            'label': r['label'],
            'type': r['type'],
            'start': r.get('start'),
            'end': r.get('end'),
            'days': []
        }
        
        if r['type'] == 'slot':
            t_start = r['start']
            
            for day in DAY_ORDER:
                if (r_idx, day) in covered_cells:
                    row_data['days'].append({'skipped': True})
                    continue
                
                entries = data_map.get((day, t_start), [])
                
                # Sort by batch
                entries.sort(key=lambda x: x.batch)
                
                is_practical = (len(entries) > 1)
                rowspan = 1
                
                # Check for merge (Practical Block of 2 hours)
                # Rows 0, 3, 6 are start of blocks in our view_rows structure
                if is_practical and r_idx in [0, 3, 6] and (r_idx + 1) < len(view_rows):
                    next_row = view_rows[r_idx+1]
                    if next_row['type'] == 'slot':
                        next_t_start = next_row['start']
                        next_entries = data_map.get((day, next_t_start), [])
                        
                        # If next slot is also practical, assume valid block merge
                        if len(next_entries) > 1:
                            rowspan = 2
                            covered_cells.add((r_idx + 1, day))

                cell_info = {
                    'entries': entries, 
                    'is_practical': is_practical,
                    'rowspan': rowspan,
                    'skipped': False
                }
                row_data['days'].append(cell_info)
        
        final_rows.append(row_data)

    return render(request, 'class_timetable/view.html', {
        'class_name': cfg['name'],
        'class_key': class_key,
        'timetable_rows': final_rows,
        'days': DAY_ORDER
    })

def delete_timetable(request, class_key):
    if class_key not in CLASS_CONFIG:
        return redirect('class_timetable:dashboard')
        
    cfg = CLASS_CONFIG[class_key]
    TimetableModel = cfg['timetable']
    TimetableModel.objects.all().delete()
    messages.warning(request, f"Timetable deleted for {cfg['name']}")
    return redirect('class_timetable:dashboard')
