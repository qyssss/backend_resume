from django.urls import path
from .views import SaveResumeView, GetResumeView, UpdateResumeView,ResumePhotoUploadAPIView,DeleteResumeView,OptimizeResumeView

urlpatterns = [
    path('save', SaveResumeView.as_view(), name='save-resume'),
    path('get', GetResumeView.as_view(), name='get-resume'),
    path('delete', DeleteResumeView.as_view(), name='delete-resume'),
    path('update', UpdateResumeView.as_view(), name='update-resume'),
    path('optimize/', OptimizeResumeView.as_view()),  # POST 创建任务
    path('optimize/<int:task_id>/', OptimizeResumeView.as_view()),  # GET 查询任务
    path('photoUpload', ResumePhotoUploadAPIView.as_view(), name='resume-photo-upload'),
]