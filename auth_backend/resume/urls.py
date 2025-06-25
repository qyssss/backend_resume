from django.urls import path
from .views import SaveResumeView, GetResumeView, UpdateResumeView,ResumePhotoUploadAPIView,DeleteResumeView,OptimizeResumeView

urlpatterns = [
    path('save', SaveResumeView.as_view(), name='save-resume'),
    path('get', GetResumeView.as_view(), name='get-resume'),
    path('delete', DeleteResumeView.as_view(), name='delete-resume'),
    path('update', UpdateResumeView.as_view(), name='update-resume'),
    path('optimize', OptimizeResumeView.as_view(), name='optimize-resume'),
    path('photoUpload', ResumePhotoUploadAPIView.as_view(), name='resume-photo-upload'),
]