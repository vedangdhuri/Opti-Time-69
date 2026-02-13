### Planner Response

The project is a **Timetable Management System** built with **Django**. It appears to have two parallel modules for handling timetables: a general [timetable](cci:1://file:///d:/PROGRAMMING/Main/made_with_anti/timetable/views.py:8:0-95:68) app and a more specialized `class_timetable` app (which seems to be the active focus for recent features like parallel practical sessions).

Here is the workflow of the project, focusing on the core `class_timetable` generation logic:

### 1. High-Level Architecture
The project is divided into three main applications:
*   **`myapp`**: Handles User Authentication (Login, Signup), User Profile, Main Dashboard, and general feedback/chat features.
*   **`class_timetable`** (Active): The core module for generating class-specific timetables (e.g., TYCO A, SYCO B) using a heuristic algorithm.
*   **[timetable](cci:1://file:///d:/PROGRAMMING/Main/made_with_anti/timetable/views.py:8:0-95:68)**: A more generalized model-driven approach (likely an earlier version or alternative implementation).

---

### 2. The Core Workflow (User Journey)

#### **Step 1: Dashboard & Navigation**
*   **User Action:** detailed in [myapp/views.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/myapp/views.py:0:0-0:0).
*   Users log in and land on the main **Dashboard** (`/dashboard/`).
*   From there, they navigate to the **Class Timetable Dashboard** (`/class-timetable/`) to select a specific class (e.g., "Third Year Computer - Div A").

#### **Step 2: Input Data Configuration**
*   **User Action:** Inputs subject and teacher constraints.
*   **Process:**
    *   The user selects a class (e.g., `tyco_a`).
    *   The system loads the specific input form (e.g., `TycoAInputForm`) defined in [class_timetable/forms.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/forms.py:0:0-0:0).
    *   **Data Points:**
        *   **Teacher Name**
        *   **Subject Name**
        *   **Theory Credits:** Determines the number of 1-hour lectures.
        *   **Practical Credits:** Determines the number of 2-hour lab blocks.

#### **Step 3: Timetable Generation ( The "Magic" )**
*   **User Action:** Clicks the "Generate" button.
*   **Code Reference:** [class_timetable/utils.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/utils.py:0:0-0:0) -> [generate_timetable_for_class(class_key)](cci:1://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/utils.py:65:0-348:28).
*   **Algorithm Logic:**
    1.  **Clear Schedule:** Deletes any existing entries for that class.
    2.  **Process Requests:** Expands user inputs into "Theory Slots" (1hr) and "Practical Blocks" (2hrs/week).
    3.  **Phase A - Practicals (Hard Constraint):**
        *   Creates pools for batches (A1, A2, A3).
        *   Uses a **Randomized Greedy Approach** to find valid "trios" of teachers for the 3 batches that don't violate external constraints (e.g., checking if a teacher is busy in TYCO B while scheduling TYCO A).
        *   Places these trios in 2-hour blocks (e.g., 10-12, 12:45-2:45).
    4.  **Phase B - Theory:**
        *   Fills the remaining 1-hour slots with theory lectures.
        *   Enforces a limit of **max 2 lectures per subject per day**.
    5.  **Phase C - Fillers:**
        *   Fills generic empty slots with "Extra" lectures or "Library" to ensure no gaps.
    6.  **Save:** Commits the generated schedule to the class-specific Timetable model (e.g., `TycoATimetable`).

#### **Step 4: Viewing & Exporting**
*   **User Action:** User is redirected to the View page (`/class-timetable/view/tyco_a/`).
*   **Display Logic:** [class_timetable/views.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/views.py:0:0-0:0) prepares the data grid.
    *   It intelligently **merges cells** (rowspan) for 2-hour practical blocks so they appear as a single block in the UI.
    *   It handles formatting (Breakfast/Lunch breaks are hardcoded strings in the view).
*   **Export:** (As per recent tasks) The user can download this view as PNG, PDF, or Excel.

---

### 3. Key Files Structure

| File Path | Purpose |
| :--- | :--- |
| **[class_timetable/utils.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/utils.py:0:0-0:0)** | **Critical.** Contains the [generate_timetable_for_class](cci:1://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/utils.py:65:0-348:28) function and the entire scheduling algorithm (conflict checking, batch processing). |
| **[class_timetable/views.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/views.py:0:0-0:0)** | Handles the UI logic: Input forms, Triggering generation, and Rendering the final grid with cell merging. |
| **[class_timetable/models.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/class_timetable/models.py:0:0-0:0)** | Defines the specific tables for each class (e.g., `TycoAInput`, `TycoATimetable`) that store the configuration and results. |
| **[myapp/urls.py](cci:7://file:///d:/PROGRAMMING/Main/made_with_anti/myapp/urls.py:0:0-0:0)** | managing authentication and main dashboard routing. |