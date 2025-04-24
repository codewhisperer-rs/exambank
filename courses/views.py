from django.shortcuts import render, get_object_or_404
from .models import Book, Chapter, Section, Knowledge, Exercise
import markdown

def index(request):
    """首页视图"""
    books = Book.objects.all()
    return render(request, 'courses/index.html', {'books': books})

def book_detail(request, book_id):
    """书籍详情页，显示章节列表"""
    book = get_object_or_404(Book, id=book_id)
    chapters = book.chapters.all().order_by('number')
    return render(request, 'courses/book_detail.html', {
        'book': book,
        'chapters': chapters
    })

def chapter_detail(request, chapter_id):
    """章节详情页，显示小节列表"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    sections = chapter.sections.all().order_by('number')
    return render(request, 'courses/chapter_detail.html', {
        'chapter': chapter,
        'sections': sections
    })

def section_detail(request, section_id):
    """小节详情页，显示知识点和习题"""
    section = get_object_or_404(Section, id=section_id)
    knowledge_points = section.knowledge_points.all().order_by('order')
    exercises = section.exercises.all().order_by('order', 'number')
    
    # 转换Markdown为HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc'
    ])
    
    for knowledge in knowledge_points:
        knowledge.content = md.convert(knowledge.content)
    
    for exercise in exercises:
        exercise.content = md.convert(exercise.content)
        if exercise.explanation:
            exercise.explanation = md.convert(exercise.explanation)
    
    return render(request, 'courses/section_detail.html', {
        'section': section,
        'knowledge_points': knowledge_points,
        'exercises': exercises
    })
