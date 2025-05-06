from django.contrib import admin
from .models import Book, Chapter, Section, Knowledge, Exercise, ExerciseKnowledge, ExerciseAttempt, UserMistakeCollection, AIGeneratedExercise, AIExerciseAttempt

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')
    search_fields = ('title',)

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('book', 'number', 'title')
    list_filter = ('book',)
    search_fields = ('title',)

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'number', 'title')
    list_filter = ('chapter__book', 'chapter')
    search_fields = ('title',)

@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ('section', 'title', 'order')
    list_filter = ('section__chapter__book', 'section__chapter', 'section')
    search_fields = ('title', 'content')
    ordering = ('order',)

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('section', 'type', 'number', 'order')
    list_filter = ('type', 'section__chapter__book', 'section__chapter', 'section')
    search_fields = ('content', 'answer', 'explanation')
    ordering = ('order', 'number')

# 注册习题-知识点关联模型
@admin.register(ExerciseKnowledge)
class ExerciseKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('exercise', 'knowledge', 'relevance')
    list_filter = ('relevance',)
    search_fields = ('exercise__content', 'knowledge__title')

# 注册用户答题记录模型
@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'is_correct', 'attempt_time')
    list_filter = ('is_correct', 'attempt_time')
    search_fields = ('user__username', 'exercise__content')
    date_hierarchy = 'attempt_time'

# 注册用户错题集模型
@admin.register(UserMistakeCollection)
class UserMistakeCollectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'attempt_count', 'correct_count', 'added_at')
    list_filter = ('added_at', 'last_attempt_at')
    search_fields = ('user__username', 'exercise__content', 'notes')
    date_hierarchy = 'added_at'

# 注册AI生成习题模型
@admin.register(AIGeneratedExercise)
class AIGeneratedExerciseAdmin(admin.ModelAdmin):
    list_display = ('user', 'model_type', 'type', 'difficulty', 'created_at')
    list_filter = ('model_type', 'type', 'difficulty', 'created_at')
    search_fields = ('user__username', 'content', 'reason')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

# 注册AI习题尝试记录模型
@admin.register(AIExerciseAttempt)
class AIExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'is_correct', 'attempt_time')
    list_filter = ('is_correct', 'attempt_time')
    search_fields = ('user__username', 'exercise__content')
    date_hierarchy = 'attempt_time'
    readonly_fields = ('attempt_time',)
