from django.db import models

# 1. Class / Division
class AcademicClass(models.Model):
    name = models.CharField(max_length=50)   # TYCO-A
    semester = models.CharField(max_length=10)  # SEM-V
    academic_year = models.CharField(max_length=20)  # 2025-26

    def __str__(self):
        return f"{self.name} ({self.semester})"


# 2. Subject
class Subject(models.Model):
    SUBJECT_TYPE = [
        ('THEORY', 'Theory'),
        ('PRACTICAL', 'Practical'),
        ('ELECTIVE', 'Elective'),
    ]

    code = models.CharField(max_length=10)   # OSY, CLC
    name = models.CharField(max_length=100)
    subject_type = models.CharField(max_length=10, choices=SUBJECT_TYPE)

    def __str__(self):
        return self.code


# 3. Room
class Room(models.Model):
    room_number = models.CharField(max_length=10)  # CR-10, CR-11

    def __str__(self):
        return self.room_number


# 4. Batch
class Batch(models.Model):
    name = models.CharField(max_length=5)  # A1, A2, A3

    def __str__(self):
        return self.name


# 5. Day
class Day(models.Model):
    name = models.CharField(max_length=10)  # Monday, Tuesday

    def __str__(self):
        return self.name


# 6. Time Slot
class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"


# 7. Timetable Entry (Core Table)
class TimetableEntry(models.Model):
    academic_class = models.ForeignKey(AcademicClass, on_delete=models.CASCADE)
    day = models.ForeignKey(Day, on_delete=models.CASCADE)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)

    is_break = models.BooleanField(default=False)  # Lunch / Tea Break
    is_extra = models.BooleanField(default=False)  # Extra Lecture for filling gaps

    def __str__(self):
        return f"{self.day} | {self.time_slot}"
