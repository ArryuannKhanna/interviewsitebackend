from django.urls import path
from .views import PdfUploadView,UniqueSubjectsView,RandomQuestionView,EvaluateAnswerView,ProcessFilesView,LeaveMeetingAPIView

urlpatterns = [
    path('upload/', PdfUploadView.as_view(), name='pdf-upload'),
    path('unique-subjects/', UniqueSubjectsView.as_view(), name='unique-subjects'),
    path('random-question/<str:subject>/', RandomQuestionView.as_view(), name='random-question'),
    path('evaluate-answer/', EvaluateAnswerView.as_view(), name='evaluate-answer'),
    path('upload-files/', ProcessFilesView.as_view(), name='files-upload'),
    path('leave-meeting/', LeaveMeetingAPIView.as_view(), name='leave-meeting')
]