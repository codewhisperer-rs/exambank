from django.shortcuts import render, get_object_or_404
from .models import Book, Chapter, Section, Knowledge, Exercise
import markdown
import json

def index(request):
    """首页视图"""
    books = Book.objects.all()
    return render(request, 'courses/index.html', {'books': books})

def book_detail(request, book_id):
    """书籍详情页，显示章节列表"""
    book = get_object_or_404(Book, id=book_id)
    chapters = book.chapters.all().order_by('number')
    
    # Initialize Markdown converter (same setup as in section_detail)
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc' 
    ])
    
    # 计算所有章节下小节的总数
    total_sections = 0
    for chapter in chapters:
        if chapter.introduction:
            chapter.introduction = md.convert(chapter.introduction)
        total_sections += chapter.sections.count()
            
    return render(request, 'courses/book_detail.html', {
        'book': book,
        'chapters': chapters,
        'total_sections': total_sections  # 传递计算好的总小节数给模板
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
    """小节详情页，只显示知识点"""
    section = get_object_or_404(Section, id=section_id)
    knowledge_points = section.knowledge_points.all().order_by('order')
    exercises_count = section.exercises.count()
    
    # 转换Markdown为HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc'
    ])
    
    for knowledge in knowledge_points:
        knowledge.content = md.convert(knowledge.content)
    
    return render(request, 'courses/section_detail.html', {
        'section': section,
        'knowledge_points': knowledge_points,
        'exercises_count': exercises_count
    })

def section_exercises(request, section_id):
    """显示小节的习题页面"""
    section = get_object_or_404(Section, id=section_id)
    exercises = section.exercises.all().order_by('order', 'number')
    
    # 转换Markdown为HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc'
    ])
    
    # 获取当前小节中存在的题型
    exercise_types = exercises.values_list('type', flat=True).distinct()
    
    # 按题型分组
    grouped_exercises = {}
    
    # 题型标题映射
    type_titles = {
        'single': '一、单项选择题',
        'multiple': '二、多项选择题',
        'comprehensive': '三、综合应用题'
    }
    
    # 确定题型序号
    type_index = 1
    for exercise_type in ['single', 'multiple', 'comprehensive']:
        if exercise_type in exercise_types:
            roman_numerals = ['一', '二', '三', '四', '五']
            title = f"{roman_numerals[type_index-1]}、{dict(Exercise.TYPES)[exercise_type]}"
            grouped_exercises[exercise_type] = {
                'title': title,
                'exercises': []
            }
            type_index += 1
    
    for exercise in exercises:
        exercise.content = md.convert(exercise.content)
        if exercise.explanation:
            exercise.explanation = md.convert(exercise.explanation)
        
        # 将选项JSON转换为Python字典
        if exercise.options and isinstance(exercise.options, str):
            try:
                exercise.options_dict = json.loads(exercise.options)
            except json.JSONDecodeError:
                exercise.options_dict = {}
        elif exercise.options and isinstance(exercise.options, dict):
            exercise.options_dict = exercise.options
        else:
            exercise.options_dict = {}
        
        # 添加到对应题型组
        if exercise.type in grouped_exercises:
            grouped_exercises[exercise.type]['exercises'].append(exercise)
    
    return render(request, 'courses/section_exercises.html', {
        'section': section,
        'grouped_exercises': grouped_exercises,
        'total_count': exercises.count()
    })
