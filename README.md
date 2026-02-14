# Opti-Time: Automated Class Timetable Generator

Opti-Time is a robust Django-based application designed to automate the complex process of generating academic timetables. It handles multiple classes, subject constraints, practical batches, and teacher availability to produce conflict-free schedules.

## 🚀 Features

- **Automated Scheduling**: Generates timetables for multiple classes (e.g., SYCO A/B, TYCO A/B) simultaneously.
- **Conflict Detection**: Ensures teachers are not assigned to multiple classes at the same time.
- **Batch Management**: Automatically schedules practical sessions for distinct batches (A1, A2, A3) ensuring unique teacher assignments per slot.
- **Smart Allocation**:
  - Prioritizes practical sessions (2-hour blocks).
  - Distributes theory lectures evenly (Max 2 per day per subject).
  - Fills gaps with "Extra" lectures or Library slots to ensure no empty periods.
- **Analytics Dashboard**: Visualizes workload distribution, helping to identify underloaded or overloaded subjects/teachers.
- **Export Options**: Download timetables in PDF, Excel, and PNG formats.
- **Data Seeding**: Scripts included to populate initial sample data for testing.

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, Django Framework
- **Database**: SQLite (Default), compatible with PostgreSQL/MySQL via Django ORM
- **Frontend**: HTML5, CSS3, JavaScript
- **Libraries**:
  - `itertools` & `random`: For combinatorics and randomized slot allocation.
  - `reportlab` / `xlsxwriter` (Implied for exports): Key for document generation.

## 🧠 Algorithm

The core of Opti-Time uses a **Constrained-Based Randomized Heuristic Algorithm**. It approaches the scheduling problem in distinct phases:

1.  **Practical Scheduling (The Hard Constraint)**:
    - Uses `itertools.product` to generate valid combinations of practical subjects for batches A1, A2, and A3.
    - Enforces a strict constraint: All three teachers in a combined practical slot must be unique.
    - Checks for cross-class conflicts (e.g., Is the teacher busy in TYCO-A while needed for SYCO-B?).

2.  **Theory Scheduling**:
    - Iterates through available time slots.
    - Selects subjects from a weighted pool.
    - Applies constraints:
      - **Teacher Availability**: Checks against all other generated timetables.
      - **Daily Load**: Limits a subject to a maximum of 2 lectures per day.

3.  **Gap Filling**:
    - Scans for remaining empty slots.
    - Assigns "Extra" lectures from the available pool or "Library" slots if no teachers are available.

## 📚 Reference & Research

For a detailed analysis and bibliography, please refer to the project report:

- `report/College_Timetable_Management_System_Report.docx`

This project implements concepts from:

- **Constraint Satisfaction Problems (CSP)** in scheduling.
- **Heuristic Search Algorithms** for optimization.

_Note: Specific implementation details follow standard Operations Research methodologies for University Timetabling Problems (UTP)._

## 📦 Installation & Setup

Follow these steps to set up the project locally:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Opti-Time
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Populate Sample Data (Optional)

To load initial data for Second Year and Third Year classes:

```bash
python populate_syco_a_real.py
python populate_syco_b_real.py
python populate_tyco_a_real.py
python populate_tyco_b_real.py
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`.

## 📂 Project Structure

```
Opti-Time/
├── class_timetable/       # Main scheduling logic & models
│   ├── utils.py           # Core scheduling algorithm
│   ├── views.py           # View controllers & analytics
│   └── models.py          # Value inputs (Teachers, Subjects)
├── templates/             # HTML Templates for Dashboard/Views
├── static/                # CSS/JS assets
├── populate_*.py          # Data seeding scripts
└── manage.py              # Django CLI utility
```
