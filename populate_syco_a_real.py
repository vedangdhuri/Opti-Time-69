import os
import django
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from class_timetable.models import SycoAInput

def populate():
    print("Clearing SYCO A inputs...")
    SycoAInput.objects.all().delete()
    
    data = [
        {
            "subject": "Data Structure Using C",
            "teacher": "Mrs.T.V.Gawandi",
            "th": 3,
            "pr": 4
        },
        {
            "subject": "Database Management System",
            "teacher": "Mr.P.D.kate",
            "th": 3,
            "pr": 4
        },
        {
            "subject": "Digital Techniques",
            "teacher": "Mrs.S.A.Palav",
            "th": 3,
            "pr": 2
        },
        {
            "subject": "Object Oriented Programming Using C++",
            "teacher": "Mr.S.M.Mayekar", # Handling multiple teachers is complex, simplifying to main for now
            "th": 3,
            "pr": 4
        },
        {
            "subject": "Computer Graphics",
            "teacher": "Mr.T.M.Patil",
            "th": 1,
            "pr": 2
        },
        {
            "subject": "Essence Of Indian Constitution",
            "teacher": "Mr.J.A.Gawade",
            "th": 1,
            "pr": 0
        },
    ]
    
    for d in data:
        SycoAInput.objects.create(
            subject_name=d["subject"],
            teacher_name=d["teacher"],
            theory_credits=d["th"],
            practical_credits=d["pr"]
        )
        print(f"Added {d['subject']}")

    print("Success! SYCO A inputs populated.")

if __name__ == '__main__':
    populate()
