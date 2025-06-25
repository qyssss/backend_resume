from django.urls import path
from .views import UploadResumeView, GenerateQuestionView, health_check

urlpatterns = [
    path('upload-resume', UploadResumeView.as_view(), name='upload_resume'),
    path('generate-question', GenerateQuestionView.as_view(), name='generate_question'),
    path('health', health_check, name='health_check'),
]