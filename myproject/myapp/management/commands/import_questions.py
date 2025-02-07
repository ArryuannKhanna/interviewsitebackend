import csv
import os
from django.core.management.base import BaseCommand
from myapp.models import QuestionAnswer


class Command(BaseCommand):
    help = "Import questions and answers from CSV files into the database"

    def handle(self, *args, **kwargs):
        # Predefined mapping of filenames to subjects
        subject_mapping = {
            "gfg_Computer Network_questions_answers.csv": "Computer Networks",
            "gfg_CPP_questions_answers.csv": "Cpp",
            "gfg_Java_questions_answers.csv": "Java",
            "gfg_Javascript_questions_answers.csv": "Javascript",
            "gfg_OOPS_questions_answers.csv": "OOPs",
            "gfg_Operating System_questions_answers.csv": "Operating System",
            "gfg_Python_questions_answers.csv": "Python",
            "gfg_SQL_questions_answers.csv": "SQL",
            "gfg_System design_questions_answers.csv": "System Design"
        }

        data_dir = "Data"  # Folder where your CSV files are stored
        for filename in os.listdir(data_dir):
            if filename.endswith(".csv"):
                subject = subject_mapping.get(filename, "General")  # Default to 'General' if not mapped
                file_path = os.path.join(data_dir, filename)
                self.stdout.write(f"Importing {file_path} with subject '{subject}'...")

                with open(file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        QuestionAnswer.objects.create(
                            subject=subject,
                            question=row['Question'],
                            answer=row['Answer']
                        )
                self.stdout.write(f"Imported {file_path}")
