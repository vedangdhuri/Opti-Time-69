import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from class_timetable.models import FycoInput

def populate():
    print("Clearing FYCO inputs...")
    FycoInput.objects.all().delete()
    
    data = [
        {
            "subject": "Basic Mathematics",
            "teacher": "Mr.S.S.Olkar",
            "th": 4,
            "pr": 0
        },
        {
            "subject": "Basic Science (Physics)",
            "teacher": "Mr.A.A.Madgaonkar",
            "th": 2,
            "pr": 2
        },
        {
            "subject": "Basic Science (Chemistry)",
            "teacher": "Mr.A.G.Prabhu",
            "th": 2,
            "pr": 2
        },
        {
            "subject": "Communication Skills",
            "teacher": "Mrs.V.C.D'Souza",
            "th": 3,
            "pr": 2
        },
        {
            "subject": "Engineering Graphics",
            "teacher": "Mr.S.S.Lanjekar",
            "th": 2,
            "pr": 4
        },
        {
            "subject": "Engineering Workshop Practice",
            "teacher": "Mr.P.D.Kate",
            "th": 0,
            "pr": 4
        },
        {
            "subject": "Fundamentals of ICT",
            "teacher": "Mr.S.S.Kolapate",
            "th": 1,
            "pr": 2
        },
    ]
    
    for d in data:
        FycoInput.objects.create(
            subject_name=d["subject"],
            teacher_name=d["teacher"],
            theory_credits=d["th"],
            practical_credits=d["pr"]
        )
        print(f"Added {d['subject']}")

    print("Success! FYCO inputs populated.")

if __name__ == '__main__':
    populate()
