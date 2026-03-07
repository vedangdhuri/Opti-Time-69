from django.db import models

# Common choices for validation (optional usage, but good for consistency)
DAYS = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
]


# base abstract class to avoid repetition in code, but resulting tables will be separate in DB
class ClassInputBase(models.Model):
    subject_name = models.CharField(max_length=100)
    teacher_name = models.CharField(max_length=100)

    # Updated fields as per user request
    theory_credits = models.IntegerField(
        default=0, help_text="Theory Load (e.g. 5 means 5 hours/week)"
    )
    practical_credits = models.IntegerField(
        default=0, help_text="Practical Load (2 credits = 1 block of 2 hours)"
    )

    time_constraints = models.TextField(
        blank=True, null=True, help_text="JSON or text description of constraints"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.subject_name} ({self.teacher_name})"


class ClassTimetableBase(models.Model):
    day = models.CharField(max_length=20, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject_name = models.CharField(max_length=100)
    teacher_name = models.CharField(max_length=100)
    room = models.CharField(max_length=50, blank=True, null=True)
    # Batch identifier: 'ALL' for theory, 'A1', 'A2', 'A3' for practicals
    batch = models.CharField(max_length=10, default="ALL")

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.day} {self.start_time}-{self.end_time}: {self.subject_name} ({self.batch})"


# --- TYCO ---
class TycoInput(ClassInputBase):
    pass


class TycoTimetable(ClassTimetableBase):
    pass


# --- SYCO ---
class SycoInput(ClassInputBase):
    pass


class SycoTimetable(ClassTimetableBase):
    pass


# --- FYCO ---
class FycoInput(ClassInputBase):
    pass


class FycoTimetable(ClassTimetableBase):
    pass


# --- MASTER SUBJECTS ---
class MasterSubject(models.Model):
    CLASS_CHOICES = [
        ("tyco", "TYCO"),
        ("syco", "SYCO"),
        ("fyco", "FYCO"),
    ]
    class_name = models.CharField(max_length=10, choices=CLASS_CHOICES)
    subject_name = models.CharField(max_length=100)
    abbreviation = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="e.g. OSY, STE. Auto-used in timetable output if provided.",
    )
    teacher_name = models.CharField(max_length=100)
    theory_credits = models.IntegerField(default=0)
    practical_credits = models.IntegerField(default=0)

    class Meta:
        ordering = ["class_name", "subject_name"]
        unique_together = ("class_name", "subject_name")

    def __str__(self):
        return f"{self.get_class_name_display()} - {self.subject_name}"
