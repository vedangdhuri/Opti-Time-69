<div align="center">

# 🗓️ Opti-Time: Automated Class Timetable Generator

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-Framework-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
[![GitHub issues](https://img.shields.io/github/issues/vedangdhuri/Opti-Time-69?style=flat-square)](https://github.com/vedangdhuri/Opti-Time-69/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/vedangdhuri/Opti-Time-69?style=flat-square)](https://github.com/vedangdhuri/Opti-Time-69/commits/master)

**A robust, randomized heuristic-based system for automated academic scheduling.**

[Features](#-key-features) • [Tech Stack](#-tech-stack) • [Algorithm](#-algorithm-logic) • [Installation](#-installation--setup) • [Research](#-research--references)

</div>

---

## 📖 About The Project

**Opti-Time** is a powerful Django-based application engineered to solve the NP-hard problem of university timetabling. It automates the complex process of scheduling classes, practical batches, and teacher assignments while strictly adhering to hard constraints and optimizing for soft constraints.

It handles multiple classes (e.g., FYCO, SYCO, TYCO), subject constraints, practical batches (A1, A2, A3), and teacher availability to produce **conflict-free, optimized schedules**.

---

## 🚀 Key Features

| Feature                     | Description                                                                                                        |
| :-------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| **🤖 Automated Scheduling** | Generates valid timetables for multiple classes simultaneously with a single click.                                |
| **⚡ Conflict Detection**   | Real-time validation ensures no teacher or room is double-booked across different classes.                         |
| **🧪 Batch Management**     | Automatically handles practical sessions for distinct batches (A1, A2, A3) ensuring unique teacher assignments.    |
| **⚖️ Smart Allocation**     | Prioritizes practicals (2hr blocks), distributes theory lectures evenly (Max 2/day), and fills gaps intelligently. |
| **👨‍🏫 Faculty Timetables**   | Aggregated individual schedules for every teacher across all departments and classes.                              |
| **📚 Global Subjects**      | Define Master Subjects in Admin to automatically suggest and auto-fill workloads.                                  |
| **📈 Global Analytics**     | Dedicated institutional-level dashboards to holistically view overall validations, workload, and conflicts.        |
| **📊 Class Dashboard**      | Visualizes per-class workload distribution to identify underloaded or overloaded resources.                        |
| **🕳️ Smart Gap-Filling**    | Dynamically add extra lectures to remaining empty slots without affecting the optimized core schedule.             |
| **🔄 Dynamic Regeneration** | Seamlessly regenerate the timetable with a single click to explore and refine scheduling alternatives.             |
| **📥 Export Ready**         | Download generated timetables in professional **PDF**, **Excel**, and **PNG** formats.                             |
| **🌱 Data Seeding**         | Includes scripts to populate initial sample data for robust testing and demonstration.                             |
| **📐 Architecture Docs**    | Includes detailed System Design and multiple UML diagrams mapping out the core application logic.                  |

---

## 🛠️ Tech Stack

This project uses a modern, robust technology stack:

### Backend

- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) **Python 3.11+** - The core programming language.
- ![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white) **Django** - The high-level web framework.
- ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) **SQLite** - Local development database.
- ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white) **PostgreSQL** - Production-ready database support via `dj_database_url`.
- ![WhiteNoise](https://img.shields.io/badge/WhiteNoise-000000?style=flat-square&logo=python&logoColor=white) **WhiteNoise** - For efficient static file serving in production.

### Frontend

- ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) **HTML5** - Structuring the web pages.
- ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) **CSS3** - Styling and layout.
- ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) **JavaScript** - Dynamic interactivity.

### Libraries & Tools

- **`itertools` & `random`**: For combinatorics and randomized slot allocation.
- **`reportlab`**: For generating PDF reports.
- **`xlsxwriter`**: For Excel exports.

---

## 📐 System Architecture & UML Diagrams

Opti-Time's structure and behavior are fully documented with visual diagrams, detailing system components, object models, and algorithmic flows.

<details>
<summary><b>View Architecture & UML Diagrams</b></summary>

- **[System Architecture](system_design.png)**
- **[Use Case Diagram](use_case_diagram.png)**
- **[Class Diagram](class_diagram.png)**
- **[Sequence Diagram](sequence_diagram.png)**
- **[Activity Diagram](activity_diagram.png)**
- **[Component Diagram](component_diagram.png)**
- **[Deployment Diagram](deployment_diagram.png)**
- **[State Machine Diagram](state_machine_diagram.png)**

</details>

---

## 🧠 Algorithm Logic

The core of **Opti-Time** operates on a **Constrained-Based Randomized Heuristic Algorithm**. It approaches the scheduling problem in distinct, logical phases:

1.  **🧬 Phase 1: Practical Scheduling (Hard Constraint)**
    - Uses a cyclic rotation algorithm to assign subject trios (A1, A2, A3) to batches.
    - Guarantees 100% completion of required blocks while ensuring no batch repeat the same subject in parallel.
    - **Wait-List Logic**: If a teacher conflict occurs, sessions are queued for the next available slot.
    - **Slot Reservation**: Dynamically _reserves exact slot spaces_ before theory generation to protect required practical blocks and prevent "algorithm lockout."

2.  **🕗 Phase 2: Theory Scheduling**
    - Iterates through available time slots using a weighted pool.
    - **Constraints**:
      - **Teacher Availability**: Real-time cross-check against all other academic timetables.
      - **Daily Load**: Strict limit of maximum 2 lectures per subject per day (relaxable to 3 for backfilling).

3.  **🔄 Phase 3: Gap Filling & Optimization**
    - Scans for remaining empty slots after core generation.
    - Assigns "Extra" lectures or "Library" slots based on teacher availability to ensure no dead space in the schedule.

---

## 📦 Installation & Setup

Get the project running locally in just a few steps.

### Prerequisites

- Python 3.11 or higher
- Git

### Steps

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/vedangdhuri/Opti-Time-69.git
    cd Opti-Time
    ```

2.  **Create a Virtual Environment**

    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup**

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Seed Sample Data (Optional)**
    _Populate the database with initial data for testing:_

    ```bash
    python populate_fyco_real.py
    python populate_syco_real.py
    python populate_tyco_real.py
    ```

6.  **Run the Server**
    ```bash
    python manage.py runserver
    ```
    🎉 Open your browser and go to `http://127.0.0.1:8000/`

---

## 📂 Project Structure

```bash
Opti-Time/
├── class_timetable/       # 🧠 Main scheduling logic & models
│   ├── utils.py           # Core scheduling algorithm
│   ├── views.py           # View controllers & analytics
│   └── models.py          # Data models (Teachers, Subjects)
├── templates/             # 🎨 HTML Templates
├── static/                # 💅 CSS/JS assets
├── populate_*.py          # 🌱 Data seeding scripts
├── manage.py              # ⚙️ Django CLI utility
└── requirements.txt       # 📦 Project dependencies
```

---

## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---
