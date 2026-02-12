import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from class_timetable.models import TycoBInput

def populate():
    print("Clearing TYCO B inputs...")
    TycoBInput.objects.all().delete()
    
    data = [
        {
            "subject": "OPERATING SYSTEM",
            "teacher": "Mr. S. M. Mayekar",
            "th": 5,
            "pr": 2
        },
        {
            "subject": "SOFTWARE ENGINEERING",
            "teacher": "Mrs. P. B. Mhadgut",
            "th": 4,
            "pr": 4
        },
        {
            "subject": "ENTREPRENEURSHIP DEVELOPMENT AND STARTUPS",
            "teacher": "Mrs. T. V. Gawandi",
            "th": 1,
            "pr": 2
        },
        {
            "subject": "SEMINAR AND PROJECT INITIATION COURSE",
            "teacher": "Mr. T. C. Mhapankar",
            "th": 0,
            "pr": 2 # Assuming 2 credits for 1 block
        },
        {
            "subject": "CLOUD COMPUTING",
            "teacher": "Mr.T.M.Patil",
            "th": 4,
            "pr": 2
        },
    ]
    
    for d in data:
        TycoBInput.objects.create(
            subject_name=d["subject"],
            teacher_name=d["teacher"],
            theory_credits=d["th"],
            practical_credits=d["pr"]
        )
        print(f"Added {d['subject']}")

    print("Success! TYCO B inputs populated.")

if __name__ == '__main__':
    populate()
