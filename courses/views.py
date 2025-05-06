import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
# 确保导入所有需要的模型
from .models import Book, Chapter, Section, Exercise, Knowledge, UserExerciseAttempt, UserMistakeCollection, ExerciseKnowledge
from django.db.models import Count, Q, F, Sum, Case, When, Value, IntegerField
from django.utils import timezone
import markdown
# 确保 User 模型在模型文件中已导入，或者在这里导入
# from django.contrib.auth.models import User


def index(request):
    """首页视图"""
    books = Book.objects.all()
    return render(request, 'courses/index.html', {'books': books})

def book_detail(request, book_id):
    """书籍详情页，显示章节列表"""
    book = get_object_or_404(Book, id=book_id)
    chapters = book.chapters.all().order_by('number')
    
    # Initialize Markdown converter with LaTeX support
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc', 
        'pymdownx.arithmatex'  # 添加对 LaTeX 公式的支持
    ], extension_configs={
        'pymdownx.arithmatex': {
            'generic': True  # 使用通用的 MathJax 配置
        }
    })
    
    # 计算所有章节下小节的总数（排除章节介绍）
    total_sections = 0
    for chapter in chapters:
        if chapter.introduction:
            chapter.introduction = md.convert(chapter.introduction)
        
        # 为每个章节计算实际小节数量（排除章节介绍）
        filtered_count = 0
        for section in chapter.sections.all():
            if section.title != "章节介绍" and section.number != f"{chapter.number}.0":
                filtered_count += 1
        
        # 将过滤后的小节数量保存到章节对象中，供模板使用
        chapter.filtered_sections_count = filtered_count
        total_sections += filtered_count
            
    return render(request, 'courses/book_detail.html', {
        'book': book,
        'chapters': chapters,
        'total_sections': total_sections  # 传递计算好的总小节数给模板
    })

def chapter_detail(request, chapter_id):
    """章节详情页，显示小节列表"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    sections = chapter.sections.all().order_by('number')
    
    # 计算实际小节数量（排除章节介绍）
    filtered_sections_count = 0
    for section in sections:
        if section.title != "章节介绍" and section.number != f"{chapter.number}.0":
            filtered_sections_count += 1
    
    return render(request, 'courses/chapter_detail.html', {
        'chapter': chapter,
        'sections': sections,
        'filtered_sections_count': filtered_sections_count
    })

def section_detail(request, section_id):
    """小节详情页，只显示知识点"""
    section = get_object_or_404(Section, id=section_id)
    knowledge_points = section.knowledge_points.all().order_by('order')
    exercises_count = section.exercises.count()
    
    # 转换Markdown为HTML，添加对 LaTeX 公式的支持
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'pymdownx.arithmatex'  # 添加对 LaTeX 公式的支持
    ], extension_configs={
        'pymdownx.arithmatex': {
            'generic': True  # 使用通用的 MathJax 配置
        }
    })
    
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
    
    # 转换Markdown为HTML，添加对 LaTeX 公式的支持
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'pymdownx.arithmatex'  # 添加对 LaTeX 公式的支持
    ], extension_configs={
        'pymdownx.arithmatex': {
            'generic': True  # 使用通用的 MathJax 配置
        }
    })
    
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

@login_required
@require_POST
def submit_exercise_attempt(request):
    try:
        # 假设前端发送的是 JSON 数据
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer')

        if exercise_id is None or user_answer is None:
            return JsonResponse({'status': 'error', 'message': '缺少 exercise_id 或 user_answer'}, status=400)

        exercise = get_object_or_404(Exercise, pk=exercise_id)

        # --- 判断答案是否正确 ---
        # 注意：这里的判断逻辑可能需要根据题目类型细化
        is_correct = False
        if exercise.answer and isinstance(exercise.answer, str):
             if exercise.type == 'single':
                 is_correct = user_answer.strip().upper() == exercise.answer.strip().upper()
             # TODO: 添加其他题型 (如综合题) 的判断逻辑

        # --- 创建答题记录 ---
        attempt = UserExerciseAttempt.objects.create(
            user=request.user,
            exercise=exercise,
            is_correct=is_correct,
            user_answer=user_answer # 记录用户原始答案
        )

        # 如果答案错误，将题目加入错题集
        if not is_correct:
            mistake, created = UserMistakeCollection.objects.get_or_create(
                user=request.user,
                exercise=exercise,
                defaults={
                    'attempt_count': 1,
                    'correct_count': 0,
                    'last_attempt_at': timezone.now()
                }
            )
            
            if not created:
                # 如果这道题已经在错题集中，更新相关统计信息
                mistake.attempt_count += 1
                mistake.last_attempt_at = timezone.now()
                mistake.save()
        else:
            # 如果答对了，更新错题集中的记录（如果存在）
            try:
                mistake = UserMistakeCollection.objects.get(
                    user=request.user,
                    exercise=exercise
                )
                mistake.attempt_count += 1
                mistake.correct_count += 1
                mistake.last_attempt_at = timezone.now()
                mistake.save()
                
                # 如果连续答对3次，可以考虑从错题集中移除（可选）
                if mistake.correct_count >= 3 and (mistake.correct_count / mistake.attempt_count) >= 0.8:
                    # 达到80%的正确率且至少答对3次，可从错题集中移除
                    # 或者保留记录但标记为已掌握
                    pass
            except UserMistakeCollection.DoesNotExist:
                # 如果不在错题集中，且答对了，什么都不做
                pass

        # 返回 JSON 响应给前端
        return JsonResponse({
            'status': 'success',
            'message': '答题记录已保存',
            'is_correct': is_correct,
            'correct_answer': exercise.answer,
            'explanation': exercise.explanation
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '无效的 JSON 数据'}, status=400)
    except Exercise.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '习题不存在'}, status=404)
    except Exception as e:
        print(f"Error processing exercise attempt: {e}") # 临时打印错误
        return JsonResponse({'status': 'error', 'message': '处理请求时发生内部错误'}, status=500)

@login_required
def user_mistake_collection(request):
    """用户错题集查看页面"""
    # 获取用户的错题集
    mistakes = UserMistakeCollection.objects.filter(user=request.user).select_related(
        'exercise', 'exercise__section', 'exercise__section__chapter', 'exercise__section__chapter__book'
    ).order_by('-last_attempt_at')
    
    # 按书籍和章节分组错题
    grouped_mistakes = {}
    
    for mistake in mistakes:
        exercise = mistake.exercise
        book = exercise.section.chapter.book
        chapter = exercise.section.chapter
        
        if book.id not in grouped_mistakes:
            grouped_mistakes[book.id] = {
                'book': book,
                'chapters': {}
            }
            
        if chapter.id not in grouped_mistakes[book.id]['chapters']:
            grouped_mistakes[book.id]['chapters'][chapter.id] = {
                'chapter': chapter,
                'sections': {}
            }
            
        section_id = exercise.section.id
        if section_id not in grouped_mistakes[book.id]['chapters'][chapter.id]['sections']:
            grouped_mistakes[book.id]['chapters'][chapter.id]['sections'][section_id] = {
                'section': exercise.section,
                'mistakes': []
            }
            
        grouped_mistakes[book.id]['chapters'][chapter.id]['sections'][section_id]['mistakes'].append(mistake)
    
    # 转换为易于模板处理的列表格式
    books_list = []
    for book_id, book_data in grouped_mistakes.items():
        chapters_list = []
        for chapter_id, chapter_data in book_data['chapters'].items():
            sections_list = []
            for section_id, section_data in chapter_data['sections'].items():
                sections_list.append({
                    'section': section_data['section'],
                    'mistakes': section_data['mistakes']
                })
            
            # 按小节号排序
            sections_list.sort(key=lambda x: x['section'].number)
            
            chapters_list.append({
                'chapter': chapter_data['chapter'],
                'sections': sections_list
            })
        
        # 按章节号排序
        chapters_list.sort(key=lambda x: x['chapter'].number)
        
        books_list.append({
            'book': book_data['book'],
            'chapters': chapters_list
        })
    
    # 按书名排序
    books_list.sort(key=lambda x: x['book'].title)
    
    # 获取知识点统计
    knowledge_stats = get_user_knowledge_weakness(request.user)
    
    context = {
        'books_list': books_list,
        'knowledge_stats': knowledge_stats,
        'total_mistakes': mistakes.count()
    }
    
    return render(request, 'courses/user_mistake_collection.html', context)

def get_user_knowledge_weakness(user):
    """分析用户的知识点薄弱区域"""
    # 获取用户错题集中的所有题目
    mistake_exercises = UserMistakeCollection.objects.filter(
        user=user
    ).values_list('exercise_id', flat=True)
    
    # 获取这些习题相关联的知识点及其频率
    knowledge_weak_areas = ExerciseKnowledge.objects.filter(
        exercise_id__in=mistake_exercises
    ).values(
        'knowledge__id', 
        'knowledge__title',
        'knowledge__section__title',
        'knowledge__section__chapter__title',
        'knowledge__section__chapter__book__title'
    ).annotate(
        frequency=Count('knowledge__id')
    ).order_by('-frequency')
    
    return knowledge_weak_areas

@login_required
def recommend_exercises(request):
    """基于用户错题集推荐习题"""
    # 获取用户的薄弱知识点
    knowledge_stats = get_user_knowledge_weakness(request.user)
    
    # 获取前5个薄弱知识点ID
    weak_knowledge_ids = [item['knowledge__id'] for item in knowledge_stats[:5]]
    
    # 找出包含这些知识点且用户没做过的题目
    user_done_exercises = UserExerciseAttempt.objects.filter(
        user=request.user
    ).values_list('exercise_id', flat=True).distinct()
    
    # 推荐相关习题
    recommended_exercises = Exercise.objects.filter(
        knowledge_points__id__in=weak_knowledge_ids
    ).exclude(
        id__in=user_done_exercises
    ).distinct().select_related(
        'section', 'section__chapter', 'section__chapter__book'
    )[:20]  # 限制20题
    
    # 按知识点相关性对习题进行排序（可选，略复杂）
    
    context = {
        'recommended_exercises': recommended_exercises,
        'weak_knowledge_areas': knowledge_stats[:5]
    }
    
    return render(request, 'courses/recommended_exercises.html', context)

@login_required
@require_POST
def remove_from_mistake_collection(request):
    """从错题集中移除题目"""
    try:
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        
        if not exercise_id:
            return JsonResponse({'status': 'error', 'message': '缺少exercise_id'}, status=400)
        
        # 尝试删除记录
        result = UserMistakeCollection.objects.filter(
            user=request.user,
            exercise_id=exercise_id
        ).delete()
        
        if result[0] > 0:  # 如果至少删除了一条记录
            return JsonResponse({
                'status': 'success',
                'message': '已从错题集移除'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '题目不在错题集中'
            }, status=404)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'发生错误: {str(e)}'}, status=500)

@login_required
@require_POST
def add_mistake_note(request):
    """为错题添加笔记"""
    try:
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        note = data.get('note')
        
        if not exercise_id or note is None:
            return JsonResponse({'status': 'error', 'message': '缺少必要参数'}, status=400)
        
        # 查找或创建错题记录
        mistake, created = UserMistakeCollection.objects.get_or_create(
            user=request.user,
            exercise_id=exercise_id,
            defaults={'notes': note}
        )
        
        if not created:
            mistake.notes = note
            mistake.save()
        
        return JsonResponse({
            'status': 'success',
            'message': '笔记已保存'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'发生错误: {str(e)}'}, status=500)

@login_required
def get_exercise_detail(request, exercise_id):
    """获取习题详情的API端点"""
    try:
        exercise = get_object_or_404(Exercise, id=exercise_id)
        
        # 转换Markdown内容
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'pymdownx.arithmatex'  # 添加对 LaTeX 公式的支持
        ], extension_configs={
            'pymdownx.arithmatex': {
                'generic': True  # 使用通用的 MathJax 配置
            }
        })
        
        content = md.convert(exercise.content)
        explanation = md.convert(exercise.explanation) if exercise.explanation else ''
        
        # 构建选项信息
        options_html = ''
        if exercise.options and isinstance(exercise.options, dict):
            for key, value in exercise.options.items():
                options_html += f'<div class="option"><strong>{key}.</strong> {value}</div>'
        
        # 完整的内容
        full_content = f"{content}<div class='exercise-options mt-3'>{options_html}</div>"
        
        response_data = {
            'id': exercise.id,
            'type': exercise.type,
            'type_display': exercise.get_type_display(),
            'content': full_content,
            'answer': exercise.answer,
            'explanation': explanation,
            'section': {
                'id': exercise.section.id,
                'title': exercise.section.title,
                'number': exercise.section.number
            }
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)