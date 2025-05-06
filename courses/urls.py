from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.index, name='index'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('chapter/<int:chapter_id>/', views.chapter_detail, name='chapter_detail'),
    path('section/<int:section_id>/', views.section_detail, name='section_detail'),
    path('section/<int:section_id>/exercises/', views.section_exercises, name='section_exercises'),
    path('submit_attempt/', views.submit_exercise_attempt, name='submit_exercise_attempt'),
    
    # 用户错题集相关的URL
    path('mistake_collection/', views.user_mistake_collection, name='mistake_collection'),
    path('remove_from_mistakes/', views.remove_from_mistake_collection, name='remove_from_mistakes'),
    path('add_mistake_note/', views.add_mistake_note, name='add_mistake_note'),
    path('recommended_exercises/', views.recommend_exercises, name='recommended_exercises'),
    
    # API端点 - 修改路径与前端一致
    path('api/exercise-detail/<int:exercise_id>/', views.get_exercise_detail, name='exercise_detail_api'),
] 