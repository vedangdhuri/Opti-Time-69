from django.db import models

# Common choices
DAYS = [
    ('Monday', 'Monday'),
    ('Tuesday', 'Tuesday'),
    ('Wednesday', 'Wednesday'),
    ('Thursday', 'Thursday'),
    ('Friday', 'Friday'),
    ('Saturday', 'Saturday'),
]

# Base Abstract Classes
class ClassInputBase(models.Model):
    subject_name = models.CharField(max_length=100)
    teacher_name = models.CharField(max_length=100)
    
    theory_credits = models.IntegerField(default=0, help_text="Theory Load")
    practical_credits = models.IntegerField(default=0, help_text="Practical Load (2 credits = 1 block)")
    
    time_constraints = models.TextField(blank=True, null=True, help_text="JSON or text")

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
    batch = models.CharField(max_length=10, default='ALL') 

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.day} {self.start_time}-{self.end_time}: {self.subject_name} ({self.batch})"

# --- Models for V2 ---
# Using distinct names to avoid collision if necessary, but since they are in a different app, 
# Django names them 'class_timetable_v2_tycoainput' etc.

class TycoAInput(ClassInputBase):
    pass

class TycoATimetable(ClassTimetableBase):
    pass

class TycoBInput(ClassInputBase):
    pass

class TycoBTimetable(ClassTimetableBase):
    pass

class SycoAInput(ClassInputBase):
    pass

class SycoATimetable(ClassTimetableBase):
    pass

class SycoBInput(ClassInputBase):
    pass

class SycoBTimetable(ClassTimetableBase):
    pass
