from django.urls import path
from .views import JobRecommendationAPIView,JobAnalysisAPIView
urlpatterns = [
    path('recommend', JobRecommendationAPIView.as_view(), name='recommend-job'),
    path('analyze', JobAnalysisAPIView.as_view(), name='analyze-job'),
]