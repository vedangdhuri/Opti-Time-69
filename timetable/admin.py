from django.contrib import admin
from .models import (
    AcademicClass,
    Subject,
    Room,
    Batch,
    Day,
    TimeSlot,
    TimetableEntry
)

admin.site.register(AcademicClass)
admin.site.register(Subject)
admin.site.register(Room)
admin.site.register(Batch)
admin.site.register(Day)
admin.site.register(TimeSlot)
