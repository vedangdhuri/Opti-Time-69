import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from class_timetable.models import TycoInput

def populate():
    print("Clearing TYCO inputs...")
    TycoInput.objects.all().delete()
    
    data = [
        {
            "subject": "OPERATING SYSTEM",
            "teacher": "Mr.J.A.Gawade",
            "th": 5,
            "pr": 2
        },
        {
            "subject": "SOFTWARE ENGINEERING",
            "teacher": "Mr.A.S.Padwal",
            "th": 4,
            "pr": 4
        },
        {
            "subject": "ENTREPRENEURSHIP DEVELOPMENT AND STARTUPS",
            "teacher": "Mrs.S.A.Palav",
            "th": 1,
            "pr": 2
        },
        {
            "subject": "SEMINAR AND PROJECT INITIATION COURSE",
            "teacher": "Mr.P.D.Kate",
            "th": 0,
            "pr": 2 # Adjusted from 1 to 2 to ensure it gets a block
        },
        {
            "subject": "CLOUD COMPUTING",
            "teacher": "Mr.T.M.Patil",
            "th": 4,
            "pr": 2
        },
    ]
    
    for d in data:
        TycoInput.objects.create(
            subject_name=d["subject"],
            teacher_name=d["teacher"],
            theory_credits=d["th"],
            practical_credits=d["pr"]
        )
        print(f"Added {d['subject']}")

    print("Success! TYCO inputs populated.")

if __name__ == '__main__':
    populate()
