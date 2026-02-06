from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    max_load_per_day = models.IntegerField(default=4)

    def __str__(self):
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=50)
    capacity = models.IntegerField(default=60)
    is_lab = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ClassGroup(models.Model):
    name = models.CharField(max_length=50)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    weekly_hours = models.IntegerField(default=3)
    is_lab = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class TimeSlot(models.Model):
    day = models.CharField(max_length=20)
    slot = models.IntegerField()

    def __str__(self):
        return f"{self.day} - {self.slot}"
