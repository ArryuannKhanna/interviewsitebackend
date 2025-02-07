from django.shortcuts import render

# Create your views here.

import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from pdf2image import convert_from_path,convert_from_bytes
import pytesseract
import os
import google.generativeai as genai
from .models import QuestionAnswer
# from .models import SessionFeedback
import redis
import json
from .models import SessionFeedback

redis_client = redis.Redis(host='localhost', port=6379, db=0)


class PdfUploadView(APIView):
    os.environ['API_KEY'] = 'AIzaSyC-alNfZfEDq2a9j2-GcZ1y7KcMZf6plp8'
    genai.configure(api_key=os.environ['API_KEY'])
    # Choose a model that's appropriate for your use case.
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = '''
    You are provided a transcript of resume. Your task is to only output the skills sections.
    [INPUT]-
    John Doe
San Francisco, CA | john.doe@example.com | +1 123-456-7890 | LinkedIn Profile | GitHub Profile

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley, CA
Graduation Date: May 2025 | GPA: 3.85/4.0

Relevant coursework: Machine Learning, Software Engineering, Advanced Algorithms, Computer Systems, Database Management Systems
TECHNICAL SKILLS
Programming Languages: Python, Java, C++, JavaScript
Web Technologies: HTML, CSS, React.js, Node.js, Flask
Tools & Platforms: Git, Docker, Kubernetes, AWS (EC2, S3, Lambda)
Database Management: MySQL, PostgreSQL, MongoDB
Other: TensorFlow, PyTorch, RESTful APIs, GraphQL
EXPERIENCE
Software Development Intern
Google, Mountain View, CA
May 2024 – August 2024

Developed and optimized backend microservices in Java, reducing API response times by 30%.
Automated data pipeline workflows using Apache Airflow, improving team productivity by 20%.
Collaborated with a team of 5 engineers to build scalable, high-availability systems supporting millions of users.
Research Assistant – Machine Learning
UC Berkeley AI Lab, Berkeley, CA
August 2023 – May 2024

Designed and implemented reinforcement learning models for game AI, achieving a 20% improvement in decision-making efficiency.
Conducted research on explainable AI and published findings in IEEE Conference on Artificial Intelligence.
Full-Stack Developer
Freelance, Remote
January 2023 – Present

Built a feature-rich e-commerce platform using React.js, Flask, and PostgreSQL.
Implemented payment gateways using Stripe API, improving customer transaction efficiency.
Deployed and maintained applications on AWS, achieving 99.9% uptime.
PROJECTS
Real-Time Chat Application | GitHub Link

Developed a real-time chat application using WebSockets and Node.js.
Integrated authentication and secure messaging with JWT and bcrypt.
Achieved seamless cross-platform functionality with React Native.
Time Series Forecasting for Energy Consumption | GitHub Link

Built a predictive model using LSTMs to forecast energy usage trends with 95% accuracy.
Deployed the solution using Flask and hosted on Heroku for real-time predictions.
Personal Finance Tracker App | GitHub Link

Created a finance tracker using Django and React.js to manage budgets and investments.
Integrated expense categorization and visual analytics with Chart.js.
LEADERSHIP & EXTRACURRICULARS
President, Computer Science Club
UC Berkeley, August 2023 – May 2024

Organized hackathons and workshops on deep learning and cloud computing with 200+ participants.
Led a team of 10 to build a mentorship program, increasing participation by 40%.
Volunteer, Code.org
San Francisco, CA, June 2023 – December 2023

Taught programming basics to underrepresented high school students.
Organized weekly coding challenges, boosting engagement by 30%.
AWARDS & CERTIFICATIONS
Winner, HackMIT 2023 – Developed a blockchain-based voting platform.
AWS Certified Solutions Architect – Associate, 2024
Google Developer Scholarship, 2023
INTERESTS
Artificial Intelligence | Cybersecurity | Competitive Programming | Open Source Development

[OUTPUT]- Python, Java, C++, JavaScript, HTML, CSS, React.js, Node.js, Flask, Git, Docker, Kubernetes, AWS (EC2, S3, Lambda),MySQL, PostgreSQL, MongoDB.

Now do the same for the following INPUT.

[INPUT]-
    '''
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):

        pdf_file = request.FILES.get('pdf')
        if not pdf_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Save the file to a specific directory
        save_path = os.path.join('uploads', pdf_file.name)
        with open(save_path, 'wb') as f:
            for chunk in pdf_file.chunks():
                f.write(chunk)

        try:
            text_output = self.extract_text_from_pdf(save_path)
            print("Extracted Text:\n", text_output)

            entire_prompt = self.prompt + text_output
            response = self.model.generate_content(entire_prompt)
            print(response.text)
            return Response({"message": response.text}, status=status.HTTP_201_CREATED)

            # print("Extracted Text:\n", text_output)  # Console log the text
        except Exception as e:
            return Response({"error": f"Failed to process PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "File uploaded successfully"}, status=status.HTTP_201_CREATED)

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from all pages of a PDF file using OCR.
        """
        text = ""
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path)
        for page_number, page in enumerate(pages, start=1):
            print(f"Processing page {page_number}...")
            # Perform OCR on each page
            page_text = pytesseract.image_to_string(page)
            text += f"Page {page_number}:\n{page_text}\n"
        return text

class UniqueSubjectsView(APIView):
    """
    API endpoint to retrieve all unique subjects.
    """

    def post(self, request, *args, **kwargs):
        # Retrieve all unique subjects
        unique_subjects = QuestionAnswer.objects.values_list('subject', flat=True).distinct()
        return Response({'unique_subjects': list(unique_subjects)}, status=status.HTTP_200_OK)


class RandomQuestionView(APIView):
    """
    API to fetch a random question and answer for a given subject.
    """

    def get(self, request, subject, *args, **kwargs):
        questions = QuestionAnswer.objects.filter(subject=subject)
        if not questions.exists():
            return Response({"error": "No questions found for this subject."}, status=status.HTTP_404_NOT_FOUND)

        random_question = random.choice(questions)
        return Response({
            "question_id": random_question.id,
            "question": random_question.question
        }, status=status.HTTP_200_OK)



class EvaluateAnswerView(APIView):
    """
    API to evaluate user's answer against the correct answer.
    """
    os.environ['API_KEY'] = 'AIzaSyC-alNfZfEDq2a9j2-GcZ1y7KcMZf6plp8'
    genai.configure(api_key=os.environ['API_KEY'])
    # Choose a model that's appropriate for your use case.
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = '''
        You would be given a user's response to a question and a reference answer. Kindly evaluate the response against the reference
        and first of all output 'CORRECT' if user was correct,'PARTIALLY CORRECT' if user was somewhat correct else output 'WRONG'.Only if the user was wrong comment on why that was.
        Address the user as you are directly talking to them.
        [REFERENCE ANSWER]-
        '''
    prompt1 = '''
        [USER'S ANSWER]-
    '''

    def post(self, request, *args, **kwargs):
        question_id = request.data.get("question_id")
        user_answer = request.data.get("user_answer")

        try:
            question = QuestionAnswer.objects.get(id=question_id)
        except QuestionAnswer.DoesNotExist:
            return Response({"error": "Question not found."}, status=status.HTTP_404_NOT_FOUND)

        # Mocked evaluation logic (replace this with Gemini model integration)
        correct_answer = question.answer.lower()
        user_answer = user_answer.lower()
        entire_prompt = self.prompt + correct_answer + self.prompt1 + user_answer
        response = self.model.generate_content(entire_prompt)
        accuracy = response.text
        # accuracy = 100 if correct_answer == user_answer else 50  # Simplified logic


        return Response({
            "correct_answer": correct_answer,
            "accuracy": accuracy
        }, status=status.HTTP_200_OK)

class ProcessFilesView(APIView):
    os.environ['API_KEY'] = 'AIzaSyC-alNfZfEDq2a9j2-GcZ1y7KcMZf6plp8'
    genai.configure(api_key=os.environ['API_KEY'])
    model = genai.GenerativeModel('gemini-1.5-flash')
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        """
        Handles uploaded resume and job description files, processes them directly, and returns the output.
        """
        resume_file = request.FILES.get('resume')
        job_description_file = request.FILES.get('jobDescription')

        if not resume_file or not job_description_file:
            return Response({"error": "Both resume and job description files are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # Extract text from the uploaded files
            resume_text = self.extract_text_from_pdf(resume_file.read())
            job_description_text = self.extract_text_from_pdf(job_description_file.read())

            # Generate responses using the GenAI model
            resume_prompt = f"Extract the skills section from the following resume:\n{resume_text}"
            job_description_prompt = f"Summarize the following job description:\n{job_description_text}"

            resume_response = self.model.generate_content(resume_prompt)
            job_description_response = self.model.generate_content(job_description_prompt)

            # Return responses directly
            return Response({
                "resume_skills": resume_response.text.strip(),
                "job_summary": job_description_response.text.strip()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Failed to process files: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_text_from_pdf(self, pdf_bytes):
        """
        Extract text from all pages of a PDF file using OCR.
        """
        text = ""
        # Convert PDF bytes to images
        pages = convert_from_bytes(pdf_bytes)
        for page_number, page in enumerate(pages, start=1):
            print(f"Processing page {page_number}...")
            # Perform OCR on each page
            page_text = pytesseract.image_to_string(page)
            text += f"Page {page_number}:\n{page_text}\n"
        return text

class LeaveMeetingAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Extract session ID and user from the request
        session_id = request.data.get("session_id")
        user = request.data.get("user")

        if not session_id or not user:
            return Response({"error": "Session ID and user are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the interaction history from Redis
            # (Replace `redis_client` with your Redis setup)
            # redis_key = f"interaction:{session_id}:{user}"
            redis_key = "hello"
            interaction_history_json = redis_client.hget(redis_key, "interaction_history")

            # if not interaction_history_json:
            #     return Response({"error": "No interaction history found."}, status=status.HTTP_404_NOT_FOUND)

            # interaction_history = json.loads(interaction_history_json)

            interaction_history = [
                {
                    "question": "Can you introduce yourself and describe your professional background?",
                    "answer": "My name is John Doe, and I have 5 years of experience in software development.",
                },
                {
                    "question": "What was the most challenging project you worked on, and how did you handle it?",
                    "answer": "I worked on a large-scale e-commerce platform where scaling was a challenge. I optimized the database queries."
                },
                {
                    "question": "What are your strengths and areas for improvement?",
                    "answer": "My strengths are problem-solving and teamwork. I need to work on public speaking."
                },
                {
                    "question": "Can you explain the difference between REST and GraphQL?",
                    "answer": "REST is resource-based while GraphQL is query-based."
                },
                {
                    "question": "How do you stay updated with the latest industry trends?",
                    "answer": "I follow tech blogs and attend webinars."
                },
                {
                    "question": "Can you describe a time when you had to resolve a conflict in your team?",
                    "answer": "During a project, two team members disagreed on implementation. I mediated by discussing pros and cons."
                }
            ]

            # Generate feedback for each question and calculate skill scores
            hr_skills = 0
            communication_skills = 0
            technical_skills = 0
            total_questions = len(interaction_history)

            for interaction in interaction_history:
                question = interaction.get("question", "")
                answer = interaction.get("answer", "")

                # Example: Generate feedback and tips for each question (you can replace this logic)
                feedback = f"Good response to the question: '{question}'"
                tips = f"Consider providing more examples for better clarity."

                # Add feedback and tips back to the interaction
                interaction["feedback"] = feedback
                interaction["tips"] = tips

                # Update skill scores based on the response (customize this logic)
                hr_skills += 8  # Example score increment
                communication_skills += 7
                technical_skills += 9

            # Average the skill scores
            if total_questions > 0:
                hr_skills = hr_skills // total_questions
                communication_skills = communication_skills // total_questions
                technical_skills = technical_skills // total_questions

            # Store the session data in the database
            session_feedback, created = SessionFeedback.objects.get_or_create(
                session_id=session_id, user=user
            )
            session_feedback.interaction_history = json.dumps(interaction_history)
            session_feedback.hr_skills = hr_skills
            session_feedback.communication_skills = communication_skills
            session_feedback.technical_skills = technical_skills
            session_feedback.overall_feedback = "Overall good performance."
            session_feedback.save()

            # Remove interaction history from Redis (optional)
            redis_client.delete(redis_key)

            return Response({"message": "Meeting data processed and stored successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def get(self, request, *args, **kwargs):
    #     # Extract session ID and user from query parameters
    #     session_id = request.query_params.get("session_id")
    #     user = request.query_params.get("user")
    #
    #     if not session_id or not user:
    #         return Response({"error": "Session ID and user are required."}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     try:
    #         # Retrieve the session feedback from the database
    #         session_feedback = SessionFeedback.objects.filter(session_id=session_id, user=user).first()
    #
    #         if not session_feedback:
    #             return Response({"error": "No feedback found for the given session and user."},
    #                             status=status.HTTP_404_NOT_FOUND)
    #
    #         # Prepare the response data
    #         data = {
    #             "interaction_history": json.loads(session_feedback.interaction_history),
    #             "hr_skills": session_feedback.hr_skills,
    #             "communication_skills": session_feedback.communication_skills,
    #             "technical_skills": session_feedback.technical_skills,
    #             "overall_feedback": session_feedback.overall_feedback,
    #         }
    #         return Response(data, status=status.HTTP_200_OK)
    #
    #     except Exception as e:
    #         return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)