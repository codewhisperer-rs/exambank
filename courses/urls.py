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
    
    # AI推荐相关的URL
    path('ai_recommend/', views.ai_recommend_exercises, name='ai_recommend'),
    path('ai_recommend/get_recommendations/', views.get_ai_exercise_recommendations, name='get_ai_exercise_recommendations'),
    
    # 知识点提取与习题生成
    path('extract_knowledge/', views.extract_mistake_knowledge_points, name='extract_knowledge'),
    
    # API端点 - 修改路径与前端一致
    path('api/exercise-detail/<int:exercise_id>/', views.get_exercise_detail, name='exercise_detail_api'),
    
    # 新增 - 习题提交API端点
    path('api/submit-exercise-attempt/', views.submit_exercise_attempt, name='submit_exercise_attempt_api'),
    
    # 新增 - AI生成习题相关API
    path('api/ai-exercise-detail/<int:exercise_id>/', views.get_ai_exercise_detail, name='ai_exercise_detail_api'),
    path('api/submit-ai-exercise-attempt/', views.submit_ai_exercise_attempt, name='submit_ai_exercise_attempt_api'),
    
    # 新增 - AI习题库
    path('ai-exercises/', views.my_ai_exercises, name='my_ai_exercises'),
    path('ai-exercises/reclassify/', views.reclassify_ai_exercises_view, name='reclassify_ai_exercises'),
    path('ai-exercises/clear/', views.clear_ai_exercises_view, name='clear_ai_exercises'),
    
    # 新增 - 习题反馈
    path('submit-exercise-feedback/', views.submit_exercise_feedback, name='submit_exercise_feedback'),
] 