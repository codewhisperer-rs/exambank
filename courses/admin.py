from django.contrib import admin
from .models import Book, Chapter, Section, Knowledge, Exercise

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
