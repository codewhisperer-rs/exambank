import json
import requests
import asyncio  # 添加异步支持
import httpx  # 添加异步HTTP客户端
import aiohttp  # 添加异步HTTP库
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from asgiref.sync import sync_to_async, async_to_sync  # 添加异步转同步工具
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt  # 添加CSRF豁免装饰器
from django.db.models import Count, Q, F, Sum, Case, When, Value, IntegerField
from django.utils import timezone
import markdown
import re
import html

# 尝试导入markdownify，如果失败则提供一个简单的替代函数
try:
    from markdownify import markdownify as md_convert
except ImportError:
    # 提供一个简单的替代函数，用于处理HTML文本
    def md_convert(html_text):
        # 移除HTML标签，保留文本内容
        text = re.sub(r'<[^>]*>', ' ', html_text)
        # 替换HTML实体
        text = html.unescape(text)
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text

# 导入所有需要的模型
from .models import Book, Chapter, Section, Exercise, Knowledge, UserMistakeCollection, ExerciseKnowledge, ExerciseAttempt, AIGeneratedExercise, AIExerciseAttempt, ExerciseFeedback
import logging
import time
from django.core.paginator import Paginator
from django.contrib import messages
import random
import traceback
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

# 替换配置
# Grok API配置
GROK_API_KEY = "xai-O3QdRmxwS48SZJGgp646FnBoFyum2liAKZTEim1frYcTf8Uv6BuNcDsjLbgDGIIPlrQhotNKKGzCs8qQ"  # 实际使用时需要填入您的API密钥
GROK_API_URL = "https://api.x.ai/v1/chat/completions"  # 修复URL格式，添加https://

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-f2d0085bbb88479b9b0d7b1f2451b310"  # 实际使用时需要填入您的API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"  # 修复URL格式，添加https://

# 当前使用的模型类型，可以是 "grok" 或 "deepseek"
CURRENT_MODEL = "grok"  # 默认使用Grok

logger = logging.getLogger(__name__)

@login_required
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

@csrf_exempt  # 临时添加CSRF豁免
@require_http_methods(["POST"])
def submit_exercise_attempt(request):
    """
    提交习题尝试答案并验证结果
    
    参数:
    - exercise_id: 习题ID
    - user_answer: 用户答案
    
    返回:
    - is_correct: 是否正确
    - correct_answer: 正确答案
    - explanation: 解析
    """
    try:
        # 检查用户是否登录
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': '请先登录后再提交答案'
            }, status=401)
            
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer')

        # 验证必要参数
        if not exercise_id or user_answer is None:
            return JsonResponse({
                'status': 'error',
                'message': '缺少必要参数: exercise_id 或 user_answer'
            }, status=400)
        
        # 获取习题信息
        try:
            exercise = Exercise.objects.get(id=exercise_id)
        except Exercise.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'习题ID {exercise_id} 不存在'
            }, status=404)
        
        # 根据题目类型判断答案正确性
        is_correct = False
        
        if exercise.type == 'single':
            # 单选题比较
            is_correct = user_answer.strip() == exercise.answer.strip()
        elif exercise.type == 'multiple':
            # 多选题比较 - 将答案排序后比较
            user_choices = sorted(user_answer.strip().split(','))
            correct_choices = sorted(exercise.answer.strip().split(','))
            is_correct = user_choices == correct_choices
        else:
            # 其他题型直接比较
            is_correct = user_answer.strip() == exercise.answer.strip()
        
        # 记录用户尝试
        logger.info(f"用户 {request.user.username} 尝试习题 {exercise_id}: " +
                   f"答案 '{user_answer}' - 结果: {'正确' if is_correct else '错误'}")
        
        # 创建或更新用户习题尝试记录
        attempt = ExerciseAttempt.objects.create(
            user=request.user,
            exercise=exercise,
            is_correct=is_correct,
            user_answer=user_answer
        )
        
        # 更新错题集统计
        if not is_correct:
            mistake, created = UserMistakeCollection.objects.get_or_create(
                user=request.user,
                exercise=exercise,
                defaults={
                    'attempt_count': 1, 
                    'correct_count': 0,
                    'last_wrong_answer': user_answer, 
                    'last_attempt_at': attempt.attempt_time
                }
            )
            if not created:
                mistake.attempt_count += 1
                mistake.last_wrong_answer = user_answer
                mistake.last_attempt_at = attempt.attempt_time
                mistake.save()
        else:
            # 如果答对了，但之前有错题记录，更新正确次数
            try:
                mistake = UserMistakeCollection.objects.get(
                    user=request.user,
                    exercise=exercise
                )
                mistake.correct_count += 1
                mistake.last_attempt_at = attempt.attempt_time
                mistake.save()
            except UserMistakeCollection.DoesNotExist:
                pass
        
        # 返回结果
        return JsonResponse({
            'status': 'success',
            'is_correct': is_correct,
            'correct_answer': exercise.answer,
            'explanation': exercise.explanation
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '无效的JSON数据'
        }, status=400)
    
    except Exception as e:
        logger.error(f"提交习题尝试时出错: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }, status=500)

@login_required
def user_mistake_collection(request):
    """用户错题集查看页面"""
    # 获取用户的错题集 - 避免使用exercise_type字段
    mistakes = UserMistakeCollection.objects.filter(user=request.user).select_related(
        'exercise', 'exercise__section', 'exercise__section__chapter', 'exercise__section__chapter__book'
    ).order_by('-added_at')  # 改用added_at字段排序
    
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
    user_done_exercises = ExerciseAttempt.objects.filter(
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
            'pymdownx.arithmatex'
        ], extension_configs={
            'pymdownx.arithmatex': {
                'generic': True
            }
        })
        content = md.convert(exercise.content)
        explanation = md.convert(exercise.explanation) if exercise.explanation else ''
        
        # 获取用户在错题集中的记录
        user_mistake = None
        user_answer = None
        try:
            user_mistake = UserMistakeCollection.objects.get(
                user=request.user,
                exercise=exercise
            )
            if user_mistake.last_wrong_answer:
                user_answer = user_mistake.last_wrong_answer
            else:
                latest_attempt = ExerciseAttempt.objects.filter(
                    user=request.user,
                    exercise=exercise,
                    is_correct=False
                ).order_by('-attempt_time').first()
                if latest_attempt:
                    user_answer = latest_attempt.user_answer
        except UserMistakeCollection.DoesNotExist:
            pass

        # 获取选项信息 (增强版)
        options_dict = {}
        options_generated = False
        
        # 检查数据库中的选项是什么类型
        if exercise.options is None:
            # 选项为空，生成默认选项
            options_generated = True
        elif isinstance(exercise.options, dict):
            # 如果已经是字典，直接使用
            options_dict = exercise.options.copy()  # 创建一个副本，避免修改原始数据
        elif isinstance(exercise.options, str):
            # 如果是字符串，尝试解析为JSON
            try:
                parsed_options = json.loads(exercise.options)
                if isinstance(parsed_options, dict):
                    options_dict = parsed_options
                else:
                    options_generated = True
            except json.JSONDecodeError:
                options_generated = True
        else:
            # 其他任何情况，生成默认选项
            options_generated = True
        
        # 如果是选择题但没有有效选项，生成默认选项
        if (not options_dict or len(options_dict) == 0) and exercise.type in ['single', 'multiple']:
            options_dict = {
                'A': '选项 A (无数据)',
                'B': '选项 B (无数据)',
                'C': '选项 C (无数据)',
                'D': '选项 D (无数据)'
            }
            options_generated = True
        
        # 确保返回的选项包含预期的ABCD键
        if exercise.type in ['single', 'multiple']:
            expected_keys = ['A', 'B', 'C', 'D']
            for key in expected_keys:
                if key not in options_dict:
                    options_dict[key] = f'选项 {key} (系统补充)'
                    options_generated = True
        
        # 构建响应
        response_data = {
            'id': exercise.id,
            'type': exercise.type,
            'type_display': exercise.get_type_display(),
            'content': content,
            'options': options_dict,
            'options_generated': options_generated,
            'answer': exercise.answer,
            'user_answer': user_answer,
            'explanation': explanation,
            'section': {
                'id': exercise.section.id,
                'title': exercise.section.title,
                'number': exercise.section.number
            }
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        # 记录详细错误日志
        import traceback
        logger.error(f"Error in get_exercise_detail for exercise {exercise_id}: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({'error': '获取题目详情时发生内部错误'}, status=500)

@login_required
def ai_recommend_exercises(request):
    """使用大模型推荐习题页面"""
    context = {}
    
    # 获取用户的错题记录
    mistakes = UserMistakeCollection.objects.filter(
        user=request.user
    ).select_related(
        'exercise', 'exercise__section', 'exercise__section__chapter'
    ).order_by('-added_at')[:10]
    
    # 获取知识点薄弱区域统计
    knowledge_stats = get_user_knowledge_weakness(request.user)
    
    # 处理GET请求中的模型参数
    selected_model = request.GET.get('model', CURRENT_MODEL)
    if selected_model not in ['grok', 'deepseek']:
        selected_model = CURRENT_MODEL
        
    # 添加基本数据到上下文
    context.update({
        'mistakes': mistakes,
        'knowledge_stats': knowledge_stats,
        'selected_model': selected_model
    })
    
    return render(request, 'courses/ai_recommend.html', context)

def _prepare_recommendation_prompt(user, mistake_collections):
    """准备推荐提示词"""
    # 构建错题和知识点信息
    exercises_info = []
    for mc in mistake_collections:
        # 获取习题相关知识点
        knowledge_points = ExerciseKnowledge.objects.filter(
            exercise=mc.exercise
        ).select_related('knowledge')
        
        knowledge_titles = [kp.knowledge.title for kp in knowledge_points]
        
        # 避免使用exercise_type字段
        exercise_type_display = dict(Exercise.TYPES).get(mc.exercise.type, '未知题型')
        
        exercises_info.append({
            'exercise_id': mc.exercise.id,
            'exercise_content': mc.exercise.content.strip(),
            'exercise_type': exercise_type_display,
            'answer': mc.exercise.answer,
            'knowledge_points': knowledge_titles,
            'attempts': mc.attempt_count,
            'correct_count': mc.correct_count,
            'book_title': mc.exercise.section.chapter.book.title
        })
    
    # 获取当前用户可用的所有书籍信息
    books = Book.objects.all()
    book_list = [{'id': book.id, 'title': book.title} for book in books]
    
    # 构建提示词
    prompt = f"""
作为一个智能教育助手，请根据以下学生的错题记录，推荐5个适合该学生练习的题目。

学生的错题记录：
{json.dumps(exercises_info, ensure_ascii=False, indent=2)}

可用的书籍列表:
{json.dumps(book_list, ensure_ascii=False, indent=2)}

请生成5个习题，每个习题需要包含以下信息：
1. 题目内容
2. 题目类型（单选题、多选题或综合题）
3. 选项（如为选择题）
4. 正确答案
5. 解析
6. 难度级别（简单、中等、困难）
7. 相关知识点
8. 推荐理由
9. 所属书籍（必须从上面提供的书籍列表中选择一个最匹配的）

请确保每个习题都有一个精确的"book_title"字段，表示该题目属于哪本书。这对于正确分类习题非常重要。

请以JSON格式返回，格式如下:
[
  {{
    "content": "题目内容",
    "type": "单选题/多选题/综合题",
    "options": {{
      "A": "选项A内容",
      "B": "选项B内容",
      "C": "选项C内容",
      "D": "选项D内容"
    }},
    "answer": "正确答案",
    "explanation": "题目解析",
    "difficulty": "简单/中等/困难",
    "knowledge_points": ["知识点1", "知识点2"],
    "reason": "推荐理由",
    "book_title": "所属书籍标题"
  }},
  ...
]
"""
    
    return prompt

async def _prepare_recommendation_prompt_async(user, mistake_collections):
    """准备推荐提示词 (异步版本)"""
    # 安全地获取提示词
    return await sync_to_async(_prepare_recommendation_prompt)(user, mistake_collections)

async def _call_large_language_model_with_retry(prompt, model_type="grok", max_retries=3, timeout=60):
    """带有重试机制的大语言模型API调用函数 (异步版本)
    
    Args:
        prompt: 提示词
        model_type: 模型类型，"grok"或"deepseek"
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒）
    
    Returns:
        list: 处理后的模型响应
    """
    logger.info(f"开始异步调用{model_type}模型API（带重试机制），最大重试次数：{max_retries}，超时：{timeout}秒")
    
    # 如果API密钥未设置，使用模拟数据
    if model_type == "grok" and not GROK_API_KEY:
        logger.warning(f"{model_type} API密钥未设置，使用模拟数据")
        return _mock_ai_recommendations(model_type)
    elif model_type == "deepseek" and not DEEPSEEK_API_KEY:
        logger.warning(f"{model_type} API密钥未设置，使用模拟数据")
        return _mock_ai_recommendations(model_type)
    
    # 初始化重试计数
    retry_count = 0
    last_error = None
    
    async with httpx.AsyncClient() as client:
        while retry_count < max_retries:
            try:
                # 根据模型类型选择不同的API调用函数
                if model_type == "grok":
                    logger.info(f"尝试异步调用Grok API（尝试 {retry_count + 1}/{max_retries}）")
                    # 选择要使用的API函数
                    api_func = _call_grok_api_async
                    api_url = GROK_API_URL
                else:  # deepseek
                    logger.info(f"尝试异步调用DeepSeek API（尝试 {retry_count + 1}/{max_retries}）")
                    api_func = _call_deepseek_api_async
                    api_url = DEEPSEEK_API_URL
                
                # 发送请求前检查API端点是否可达
                try:
                    # 使用HEAD请求快速检查API端点是否可达
                    head_response = await client.head(api_url, timeout=5)
                    logger.info(f"{model_type} API端点状态码: {head_response.status_code}")
                except httpx.RequestError as e:
                    logger.warning(f"{model_type} API端点不可达: {str(e)}")
                    # 如果端点不可达，直接进入下一次重试
                    retry_count += 1
                    last_error = f"API端点不可达: {str(e)}"
                    
                    if retry_count < max_retries:
                        logger.info(f"等待2秒后重试...")
                        await asyncio.sleep(2)
                    continue
                
                # 调用相应的API函数，设置更长的超时时间
                response = await api_func(client, prompt)
                
                # 检查响应是否包含错误
                if isinstance(response, list) and len(response) > 0 and "error" in response[0]:
                    error_msg = response[0].get("error", "未知错误")
                    logger.warning(f"{model_type} API调用返回错误: {error_msg}")
                    
                    # 某些错误是不需要重试的（如认证错误）
                    if "API密钥未设置" in error_msg or "认证失败" in error_msg or "无效的API密钥" in error_msg:
                        logger.error(f"{model_type} API认证错误，不再重试: {error_msg}")
                        return response
                    
                    # 对于其他错误，继续重试
                    retry_count += 1
                    last_error = error_msg
                    
                    if retry_count < max_retries:
                        logger.info(f"等待2秒后重试...")
                        await asyncio.sleep(2)
                    continue
                
                # 如果没有错误，返回结果
                logger.info(f"成功获取{model_type} API响应")
                return response
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                logger.warning(f"{model_type} API调用异常 (尝试 {retry_count}/{max_retries}): {last_error}")
                
                if retry_count < max_retries:
                    # 增加等待时间，避免频繁请求
                    wait_time = 2 * retry_count  # 渐进式增加等待时间
                    logger.info(f"等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
        
        # 如果所有重试都失败，返回错误信息
        logger.error(f"{model_type} API在{max_retries}次尝试后仍然失败: {last_error}")
        return [{"error": f"API调用在{max_retries}次尝试后失败: {last_error}", "content": "模型调用失败，请稍后再试。"}]

async def _call_grok_api_async(client, prompt):
    """异步调用Grok API"""
    logger.info("正在异步调用Grok API...")
    
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-3-fast-beta",
        "messages": [
            {"role": "system", "content": "你是一个专业的教育助手，帮助学生根据错题记录推荐适合的练习题。请始终以JSON格式回复，确保回复内容可以被json.loads()函数解析。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = await client.post(GROK_API_URL, headers=headers, json=data, timeout=60.0)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # 解析Grok的响应格式
            ai_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"成功获取Grok API响应，长度: {len(ai_response)}")
            
            # 提取JSON部分
            json_part = ai_response
            # 尝试查找JSON开始和结束的位置
            try:
                start_idx = ai_response.find('[')
                end_idx = ai_response.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_part = ai_response[start_idx:end_idx]
            except:
                pass
                
            # 解析JSON响应
            try:
                recommendations = json.loads(json_part)
                return recommendations
            except json.JSONDecodeError as e:
                logger.error(f"无法解析Grok API返回的JSON: {str(e)}")
                logger.debug(f"原始响应: {ai_response}")
                
                # 尝试使用正则表达式提取JSON
                import re
                json_match = re.search(r'\[(.*?)\]', ai_response, re.DOTALL)
                if json_match:
                    try:
                        json_str = f"[{json_match.group(1)}]"
                        recommendations = json.loads(json_str)
                        return recommendations
                    except:
                        pass
                
                # 返回错误信息        
                return [{"error": "无法解析API响应", "content": ai_response}]
        else:
            error_msg = f"Grok API调用失败: HTTP {response.status_code}"
            logger.error(f"{error_msg} - {response.text}")
            return [{"error": error_msg}]
    except httpx.TimeoutException:
        logger.error("Grok API调用超时")
        return [{"error": "API调用超时"}]
    except Exception as e:
        logger.error(f"Grok API调用出错: {str(e)}")
        return [{"error": f"API调用异常: {str(e)}"}]

async def _call_deepseek_api_async(client, prompt):
    """异步调用DeepSeek API"""
    logger.info("正在异步调用DeepSeek API...")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的教育助手，帮助学生根据错题记录推荐适合的练习题。请始终以JSON格式回复，确保回复内容可以被json.loads()函数解析。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = await client.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30.0)
        
        if response.status_code == 200:
            response_data = response.json()
            
            # 解析DeepSeek的响应格式
            ai_response = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"成功获取DeepSeek API响应，长度: {len(ai_response)}")
            
            # 提取JSON部分
            json_part = ai_response
            # 尝试查找JSON开始和结束的位置
            try:
                start_idx = ai_response.find('[')
                end_idx = ai_response.rfind(']') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_part = ai_response[start_idx:end_idx]
            except:
                pass
                
            # 解析JSON响应
            try:
                recommendations = json.loads(json_part)
                return recommendations
            except json.JSONDecodeError as e:
                logger.error(f"无法解析DeepSeek API返回的JSON: {str(e)}")
                logger.debug(f"原始响应: {ai_response}")
                
                # 尝试使用正则表达式提取JSON
                import re
                json_match = re.search(r'\[(.*?)\]', ai_response, re.DOTALL)
                if json_match:
                    try:
                        json_str = f"[{json_match.group(1)}]"
                        recommendations = json.loads(json_str)
                        return recommendations
                    except:
                        pass
                
                # 返回错误信息        
                return [{"error": "无法解析API响应", "content": ai_response}]
        else:
            error_msg = f"DeepSeek API调用失败: HTTP {response.status_code}"
            logger.error(f"{error_msg} - {response.text}")
            return [{"error": error_msg}]
    except httpx.TimeoutException:
        logger.error("DeepSeek API调用超时")
        return [{"error": "API调用超时"}]
    except Exception as e:
        logger.error(f"DeepSeek API调用出错: {str(e)}")
        return [{"error": f"API调用异常: {str(e)}"}]

@login_required
@require_POST
async def get_ai_exercise_recommendations_async(request):
    """异步生成AI习题推荐"""
    user = request.user
    model_type = request.POST.get('model_type', 'grok')  # 默认使用grok
    
    # 使用sync_to_async安全地获取用户名
    username = await sync_to_async(lambda: user.username)()
    logger.info(f"开始为用户 {username} 生成AI习题推荐（使用{model_type}模型 - 异步版本）")
    
    # 1. 获取用户的错题集
    mistake_collections = await sync_to_async(list)(UserMistakeCollection.objects.filter(
        user=user
    ).select_related(
        'exercise', 'exercise__section', 'exercise__section__chapter', 'exercise__section__chapter__book'
    ))
    
    if not mistake_collections:
        # 如果没有错题集，随机推荐一些知识点
        logger.info(f"用户 {username} 没有错题集，使用随机知识点生成推荐")
        mistake_count = 0
    else:
        mistake_count = len(mistake_collections)
        logger.info(f"用户 {username} 有 {mistake_count} 条错题记录")
    
    # 2. 准备提示词
    prompt = await _prepare_recommendation_prompt_async(user, mistake_collections)
    logger.info(f"为用户 {username} 生成的提示词长度: {len(prompt)} 字符")
    
    # 3. 使用大语言模型生成推荐习题
    try:
        # 调用大模型获取推荐结果
        raw_recommendations = await _call_large_language_model_with_retry(prompt, model_type)
        
        # 记录原始返回
        logger.info(f"AI模型返回的原始推荐数: {len(raw_recommendations) if isinstance(raw_recommendations, list) else 'not a list'}")
        
        # 处理响应结果 - 将同步函数包装为异步
        processed_results = await sync_to_async(_post_process_recommendations)(raw_recommendations)
        
        # 保存到数据库
        for item in processed_results:
            try:
                # 确定关联的书籍，如果有
                book = None
                if 'book_title' in item and item['book_title']:
                    # 尝试按书名查找
                    books = await sync_to_async(list)(Book.objects.filter(title__icontains=item['book_title']))
                    if books:
                        book = books[0]
                
                # 创建AI习题 - 使用异步创建方式
                exercise_data = {
                    'user': user,
                    'content': item['content'],
                    'type': item.get('type', 'comprehensive'),
                    'difficulty': item.get('difficulty', '中等'),
                    'knowledge_points': item.get('knowledge_points', []),
                    'options': item.get('options', {}),
                    'answer': item.get('answer', ''),
                    'explanation': item.get('explanation', ''),
                    'reason': item.get('reason', ''),
                    'book': book,
                    'model_type': model_type
                }
                
                # 将类型值标准化
                if exercise_data['type'] == '单选题' or exercise_data['type'] == '单项选择题' or exercise_data['type'] == '选择题':
                    exercise_data['type'] = 'single'
                elif exercise_data['type'] == '多选题' or exercise_data['type'] == '多项选择题':
                    exercise_data['type'] = 'multiple'
                elif exercise_data['type'] == '综合题':
                    exercise_data['type'] = 'comprehensive'
                
                # 使用sync_to_async包装创建操作
                exercise = await sync_to_async(AIGeneratedExercise.objects.create)(**exercise_data)
                
                # 记录创建成功
                logger.info(f"成功创建AI习题: ID={exercise.id}, 类型={exercise.type}, 难度={exercise.difficulty}")
                
            except Exception as e:
                logger.error(f"保存AI习题时发生错误: {str(e)}")
        
        # 返回JSON响应
        return JsonResponse({
            'status': 'success',
            'message': f'成功生成 {len(processed_results)} 道习题',
            'recommendations': processed_results,
            'mistake_count': mistake_count,
            'redirect': '/ai-exercises/'
        })
        
    except Exception as e:
        logger.error(f"生成AI习题推荐时出错: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'生成习题时出错: {str(e)}',
            'redirect': None
        })

def _post_process_recommendations(recommendations):
    """处理和标准化推荐结果，确保每个题目都有合适的选项和答案"""
    processed_items = []
    
    for item in recommendations:
        # 如果item是错误消息，直接添加并跳过
        if 'error' in item:
            processed_items.append(item)
            continue
            
        # 创建新的处理过的项目
        processed_item = item.copy() if isinstance(item, dict) else {}
        
        # 确保基本字段存在
        if not isinstance(processed_item, dict):
            processed_item = {"content": str(processed_item)}
        
        # 设置默认值
        if 'content' not in processed_item or not processed_item['content']:
            processed_item['content'] = "无题目内容"
        
        if 'type' not in processed_item or not processed_item['type']:
            # 尝试从内容推断题目类型
            content = processed_item['content'].lower()
            # 检测单选题的特征
            single_choice_patterns = [
                '单选题',
                '单项选择题',
                '以下选项中.*?正确的是',
                '下列.*?正确的是',
                '下列.*?最合适的是',
                '下列.*?哪一项',
                '下列.*?哪一个',
                '下列.*?哪一种',
                '以下.*?哪个',
            ]
            
            # 检测多选题的特征
            multiple_choice_patterns = [
                '多选题',
                '多项选择题',
                '以下选项中.*?正确的有',
                '下列.*?正确的有',
                '下列.*?哪些',
                '以下.*?哪些'
            ]
            
            is_single_choice = False
            is_multiple_choice = False
            
            import re
            # 检查是否是单选题
            for pattern in single_choice_patterns:
                if re.search(pattern, content):
                    is_single_choice = True
                    break
                    
            # 检查是否是多选题
            for pattern in multiple_choice_patterns:
                if re.search(pattern, content):
                    is_multiple_choice = True
                    break
            
            # 如果有选项说明符号但没有明确的类型指示，默认为单选题
            option_indicators = [r'[Aa][.、）)]', r'（[Aa]）', r'\([Aa]\)', r'选项[Aa][：:]']
            has_options = False
            for pattern in option_indicators:
                if re.search(pattern, processed_item['content']):
                    has_options = True
                    break
            
            # 确定最终类型
            if is_multiple_choice:
                processed_item['type'] = 'multiple'
            elif is_single_choice or has_options:
                processed_item['type'] = 'single'
            else:
                processed_item['type'] = 'comprehensive'
        
        # 处理选项
        if 'options' not in processed_item or not processed_item['options']:
            # 尝试从内容中提取选项
            content = processed_item['content']
            options = {}
            
            # 多种可能的选项格式
            option_patterns = [
                r'([A-D])[.、）)](.*?)(?=(?:[A-D][.、）)])|$)',  # A. 选项内容
                r'（([A-D])）(.*?)(?=(?:（[A-D]）)|$)',             # （A）选项内容
                r'\(([A-D])\)(.*?)(?=(?:\([A-D]\))|$)',            # (A)选项内容
                r'选项([A-D])[：:](.*?)(?=(?:选项[A-D][：:])|$)'    # 选项A：选项内容
            ]
            
            import re
            options_found = False
            
            for pattern in option_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    for key, value in matches:
                        options[key.strip()] = value.strip()
                    options_found = True
                    break
            
            # 如果找到选项，将其从题目内容中移除以避免重复
            if options_found:
                # 尝试找到选项开始的位置
                option_start_patterns = [
                    r'[A-D][.、）)]',  # A.
                    r'（[A-D]）',      # （A）
                    r'\([A-D]\)',      # (A)
                    r'选项[A-D][：:]'   # 选项A：
                ]
                
                for pattern in option_start_patterns:
                    match = re.search(pattern, content)
                    if match:
                        # 如果找到，截取到选项开始前的内容
                        processed_item['content'] = content[:match.start()].strip()
                        break
            
            # 如果找到了选项或者题目类型是选择题，添加选项
            if options or processed_item['type'] in ['single', 'multiple']:
                # 如果没有足够的选项（至少有四个ABCD），补充默认选项
                for key in ['A', 'B', 'C', 'D']:
                    if key not in options:
                        options[key] = f'选项{key}'
                
                processed_item['options'] = options
        
        # 确保答案格式正确
        if 'answer' not in processed_item or not processed_item['answer']:
            if processed_item['type'] == 'single':
                processed_item['answer'] = 'A'  # 默认答案
            elif processed_item['type'] == 'multiple':
                processed_item['answer'] = 'A,B'  # 默认答案
            else:
                processed_item['answer'] = '略'
        
        # 确保有知识点
        if 'knowledge_points' not in processed_item or not processed_item['knowledge_points']:
            processed_item['knowledge_points'] = ['未指定知识点']
        elif isinstance(processed_item['knowledge_points'], str):
            # 如果知识点是字符串，转换为列表
            processed_item['knowledge_points'] = [processed_item['knowledge_points']]
        
        # 确保有解析
        if 'explanation' not in processed_item or not processed_item['explanation']:
            processed_item['explanation'] = '无解析'
        
        # 确保有难度
        if 'difficulty' not in processed_item or not processed_item['difficulty']:
            processed_item['difficulty'] = '中等'
        
        # 确保有推荐理由
        if 'reason' not in processed_item or not processed_item['reason']:
            processed_item['reason'] = '基于您的学习情况推荐'
        
        processed_items.append(processed_item)
    
    return processed_items

@csrf_exempt  # 临时添加CSRF豁免
@require_http_methods(["POST"])
async def submit_ai_exercise_attempt(request):
    """处理用户对AI生成习题的答题提交"""
    try:
        # 解析前端提交的JSON数据
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer', '')
        
        # 如果没有传入习题ID，返回错误
        if not exercise_id:
            return JsonResponse({
                'status': 'error',
                'message': '缺少习题ID'
            }, status=400)
        
        # 获取习题信息
        try:
            exercise = await sync_to_async(AIGeneratedExercise.objects.get)(id=exercise_id, user=request.user)
        except AIGeneratedExercise.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '习题不存在或无权访问'
            }, status=404)
        
        # 判断答案是否正确
        is_correct = False
        
        # 处理不同类型题目的答案比对
        if exercise.type == 'single' or exercise.type == 'multiple':
            # 单选和多选题比对
            # 注意：答案格式可能是"A"或"A,B,C"
            correct_answers = exercise.answer.replace(' ', '').split(',')
            user_answers = user_answer.replace(' ', '').split(',')
            
            # 排序后比较，忽略顺序差异
            is_correct = sorted(correct_answers) == sorted(user_answers)
        else:
            # 综合题直接比对（这里可以根据需要实现更复杂的评分逻辑）
            is_correct = user_answer.strip() == exercise.answer.strip()
        
        # 记录用户尝试
        attempt = await sync_to_async(AIExerciseAttempt.objects.create)(
            user=request.user,
            exercise=exercise,
            is_correct=is_correct,
            user_answer=user_answer
        )
        
        # 构建响应
        response_data = {
            'status': 'success',
            'is_correct': is_correct,
            'correct_answer': exercise.answer,
            'explanation': exercise.explanation
        }
        
        # 如果答案错误，可能需要添加到错题集
        if not is_correct:
            # 这里可以根据需要实现错题集功能
            pass
        
        return JsonResponse(response_data)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'JSON格式错误'
        }, status=400)
    
    except Exception as e:
        logger.error(f"提交AI习题尝试时出错: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }, status=500)

@login_required
async def get_ai_exercise_detail(request, exercise_id):
    """获取AI生成习题的详细信息"""
    try:
        # 获取习题信息
        exercise = await sync_to_async(AIGeneratedExercise.objects.get)(id=exercise_id, user=request.user)
        
        # 构建响应数据
        response_data = {
            'id': exercise.id,
            'content': exercise.content,
            'type': exercise.type,
            'options': exercise.options,
            'answer': exercise.answer,
            'explanation': exercise.explanation,
            'difficulty': exercise.difficulty,
            'knowledge_points': exercise.knowledge_points,
            'reason': exercise.reason
        }
        
        return JsonResponse(response_data)
    except AIGeneratedExercise.DoesNotExist:
        return JsonResponse({'error': '习题不存在或无权访问'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
async def extract_mistake_knowledge_points(request):
    """从用户错题中提取知识点并基于大模型生成相关练习题"""
    # 安全获取用户，避免在异步上下文中触发同步数据库操作
    user_id = await sync_to_async(lambda: request.user.id)()
    
    if request.method == 'GET':
        # 使用user_id安全地查询错题集
        mistakes = await sync_to_async(list)(UserMistakeCollection.objects.filter(
            user_id=user_id
        ).select_related(
            'exercise', 'exercise__section', 'exercise__section__chapter'
        ).order_by('-added_at')[:10])  # 最近10道错题
        
        # 准备上下文
        context = {
            'mistakes': mistakes,
            'extracted_knowledge': None,
            'generated_exercises': None,
            'error_message': None
        }
        
        return render(request, 'courses/extract_knowledge.html', context)
    
    elif request.method == 'POST':
        try:
            action = request.POST.get('action')
            
            # 使用user_id安全地查询错题集
            mistakes = await sync_to_async(list)(UserMistakeCollection.objects.filter(
                user_id=user_id
            ).select_related(
                'exercise', 'exercise__section', 'exercise__section__chapter'
            ).order_by('-added_at')[:10])  # 最近10道错题
            
            if action == 'extract_knowledge':
                # 提取知识点
                extracted_knowledge = await _extract_knowledge_from_mistakes_async(mistakes)
                
                # 准备上下文
                context = {
                    'mistakes': mistakes,
                    'extracted_knowledge': extracted_knowledge,
                    'generated_exercises': None
                }
                
                return render(request, 'courses/extract_knowledge.html', context)
                
            elif action == 'generate_exercises':
                # 获取用户指定的知识点
                selected_knowledge = request.POST.getlist('selected_knowledge')
                
                if not selected_knowledge:
                    raise ValueError("请至少选择一个知识点")
                
                # 获取用户对象，用于保存生成的习题
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = await sync_to_async(User.objects.get)(id=user_id)
                
                # 根据选择的知识点生成练习题
                generated_exercises = await _generate_exercises_from_knowledge_async(selected_knowledge, user)
                
                # 提取所有错题的知识点
                extracted_knowledge = await _extract_knowledge_from_mistakes_async(mistakes)
                
                # 准备上下文
                context = {
                    'mistakes': mistakes,
                    'extracted_knowledge': extracted_knowledge,
                    'generated_exercises': generated_exercises
                }
                
                return render(request, 'courses/extract_knowledge.html', context)
            
            else:
                raise ValueError("未知的操作类型")
                
        except Exception as e:
            # 出错处理
            context = {
                'mistakes': mistakes if 'mistakes' in locals() else [],
                'error_message': f'处理错误: {str(e)}',
                'extracted_knowledge': None,
                'generated_exercises': None
            }
            
            return render(request, 'courses/extract_knowledge.html', context)

async def _extract_knowledge_from_mistakes_async(mistakes):
    """使用大模型从错题中异步提取知识点"""
    if not mistakes:
        return []
    
    # 准备错题内容
    exercise_contents = []
    for mistake in mistakes:
        exercise_contents.append({
            'id': mistake.exercise.id,
            'content': mistake.exercise.content,
            'answer': mistake.exercise.answer,
            'type': mistake.exercise.type,
            'user_answer': mistake.last_wrong_answer or None
        })
    
    # 构建提示词
    prompt = f"""
分析以下这些习题，提取出它们涉及的关键知识点。每个知识点应该是具体的、精确的概念或技术。

习题内容:
{json.dumps(exercise_contents, ensure_ascii=False, indent=2)}

请提取出至少5个关键知识点，每个知识点请用简短的短语表示（不超过10个字），并附带简要解释（不超过50个字）。
格式如下:
[
  {{
    "knowledge_point": "知识点名称",
    "explanation": "简要解释",
    "related_exercise_ids": [相关习题ID]
  }},
  ...
]
"""
    
    # 调用大模型API获取知识点
    try:
        # 使用当前设置的默认模型
        extracted_knowledge = await _call_large_language_model_with_retry(prompt, CURRENT_MODEL)
        return extracted_knowledge
    except Exception as e:
        logger.error(f"调用大模型提取知识点时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []

async def _generate_exercises_from_knowledge_async(knowledge_points, user=None):
    """根据知识点异步生成相关练习题，并保存到数据库"""
    if not knowledge_points:
        return []
    
    # 获取所有书籍信息
    books = await sync_to_async(list)(Book.objects.all())
    book_list = [{'id': book.id, 'title': book.title} for book in books]
    
    # 构建提示词
    prompt = f"""
根据以下知识点，生成相关的练习题：
{', '.join(knowledge_points)}

可用的书籍列表:
{json.dumps(book_list, ensure_ascii=False, indent=2)}

请为每个知识点生成1-2道练习题，包括题目内容、选项（如适用）和答案。
每道题应该清晰、具体，并能够有效测试对该知识点的理解。

重要：对于每道题目，请仔细判断它最应该属于哪本书籍，并在"book_title"字段中提供书籍标题。
这对于正确分类习题非常重要。

请以JSON格式返回，格式如下:
[
  {{
    "content": "题目内容",
    "type": "single/multiple", // 单选或多选
    "options": {{
      "A": "选项A内容",
      "B": "选项B内容",
      "C": "选项C内容",
      "D": "选项D内容"
    }},
    "answer": "正确答案", // 单选题为A/B/C/D之一，多选题为多个选项以逗号分隔，如"A,C"
    "explanation": "解析",
    "knowledge_point": "相关知识点",
    "book_title": "所属书籍标题" // 必须从上面提供的书籍列表中选择一个最匹配的
  }},
  ...
]
"""
    
    # 调用大模型API生成练习题
    try:
        # 使用当前设置的默认模型
        generated_exercises = await _call_large_language_model_with_retry(prompt, CURRENT_MODEL)
        
        # 如果提供了用户，则将生成的习题保存到数据库
        if user and isinstance(generated_exercises, list):
            # 获取所有书籍的字典
            books_dict = {book.title: book for book in books}
            
            saved_exercises = []
            for item in generated_exercises:
                if isinstance(item, dict) and 'content' in item:
                    try:
                        # 确定题目类型
                        exercise_type = 'single'
                        if item.get('type') == '多选题' or item.get('type') == 'multiple':
                            exercise_type = 'multiple'
                        elif item.get('type') == 'comprehensive':
                            exercise_type = 'comprehensive'
                        
                        # 获取知识点
                        knowledge_point = item.get('knowledge_point', '')
                        if not knowledge_point and 'knowledge_points' in item:
                            knowledge_point = item.get('knowledge_points', '')
                        
                        knowledge_points_list = []
                        if knowledge_point:
                            if isinstance(knowledge_point, list):
                                knowledge_points_list = knowledge_point
                            else:
                                knowledge_points_list = [knowledge_point]
                        
                        # 根据题目内容找到对应的书籍
                        book = None
                        book_title = item.get('book_title')
                        if book_title and book_title in books_dict:
                            book = books_dict[book_title]
                        
                        # 创建习题数据字典
                        exercise_data = {
                            'user': user,
                            'model_type': 'knowledge_extraction',  # 标记来源
                            'type': exercise_type,
                            'content': item['content'],
                            'options': item.get('options', {}),
                            'answer': item.get('answer', ''),
                            'explanation': item.get('explanation', ''),
                            'knowledge_points': knowledge_points_list,
                            'reason': '基于知识点提取生成',
                            'difficulty': 'medium',  # 默认中等难度
                            'book': book  # 使用题目指定的书籍
                        }
                        
                        # 保存到数据库 - 使用async_to_sync处理
                        exercise = await sync_to_async(AIGeneratedExercise.objects.create)(**exercise_data)
                        
                        # 添加数据库ID到返回的习题中，以便前端使用
                        item['db_id'] = exercise.id
                        saved_exercises.append(exercise)
                    except Exception as e:
                        logger.error(f"保存习题时出错: {str(e)}")
                        continue
            
            logger.info(f"已成功保存 {len(saved_exercises)} 道习题到数据库")
        
        return generated_exercises
    except Exception as e:
        logger.error(f"调用大模型生成练习题时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []

async def _call_large_language_model(prompt, model_type="grok"):
    """调用大语言模型API获取推荐（异步版本）"""
    # 使用异步API
    logger.info(f"使用{model_type} API生成回答（异步版本）")
    return await _call_large_language_model_with_retry(prompt, model_type)

@login_required
def my_ai_exercises(request):
    """用户的AI习题库 - 显示所有AI生成的习题"""
    # 获取当前用户的所有AI生成习题
    ai_exercises = AIGeneratedExercise.objects.filter(
        user=request.user
    ).select_related('book').order_by('-created_at')
    
    # 按来源/模型类型分组
    by_model = {}
    for exercise in ai_exercises:
        model_type = exercise.model_type
        if model_type not in by_model:
            by_model[model_type] = []
        by_model[model_type].append(exercise)
    
    # 按书籍分组
    by_book = {}
    for exercise in ai_exercises:
        if exercise.book:
            book_id = exercise.book.id
            book_title = exercise.book.title
            if book_id not in by_book:
                by_book[book_id] = {
                    'title': book_title,
                    'exercises': []
                }
            by_book[book_id]['exercises'].append(exercise)
    
    # 预先统计不同类型的习题数量
    single_count = 0
    multiple_count = 0
    comprehensive_count = 0
    
    for exercise in ai_exercises:
        if exercise.type == 'single':
            single_count += 1
        elif exercise.type == 'multiple':
            multiple_count += 1
        elif exercise.type == 'comprehensive':
            comprehensive_count += 1
    
    # 获取用户的练习记录
    attempt_records = AIExerciseAttempt.objects.filter(
        user=request.user
    ).order_by('-attempt_time')
    
    # 构建尝试记录字典，便于快速查找
    attempts_by_exercise = {}
    for attempt in attempt_records:
        exercise_id = attempt.exercise.id
        if exercise_id not in attempts_by_exercise:
            attempts_by_exercise[exercise_id] = []
        attempts_by_exercise[exercise_id].append(attempt)
    
    # 获取未分类习题的数量
    unclassified_count = AIGeneratedExercise.objects.filter(
        user=request.user, 
        book__isnull=True
    ).count()
    
    context = {
        'ai_exercises': ai_exercises,
        'by_model': by_model,
        'by_book': by_book,
        'attempts_by_exercise': attempts_by_exercise,
        'total_count': ai_exercises.count(),
        'single_count': single_count,
        'multiple_count': multiple_count,
        'comprehensive_count': comprehensive_count,
        'unclassified_count': unclassified_count
    }
    
    return render(request, 'courses/my_ai_exercises.html', context)

@login_required
def reclassify_ai_exercises_view(request):
    """重新分类AI习题的视图函数"""
    if request.method == 'POST':
        model_type = request.POST.get('model_type', 'grok')
        
        # 获取所有未分类的习题
        unclassified_exercises = AIGeneratedExercise.objects.filter(
            user=request.user,
            book__isnull=True
        )
        total_count = unclassified_exercises.count()
        
        if total_count == 0:
            messages.info(request, '没有需要分类的习题')
            return redirect('courses:my_ai_exercises')
        
        # 开始异步任务
        messages.success(request, f'开始对 {total_count} 道习题进行分类，这可能需要几分钟时间。完成后结果将显示在习题库中。')
        
        # 这里应该启动Celery任务，但为了简单起见，我们直接调用命令
        from django.core.management import call_command
        try:
            # 分批处理，每批5个
            call_command('reclassify_ai_exercises', batch=5, model=model_type)
            messages.success(request, '分类完成！')
        except Exception as e:
            messages.error(request, f'分类过程中出错: {str(e)}')
        
        return redirect('courses:my_ai_exercises')
    
    return redirect('courses:my_ai_exercises')

@login_required
def clear_ai_exercises_view(request):
    """清空AI习题库的视图函数"""
    if request.method == 'POST':
        confirm = request.POST.get('confirm') == 'true'
        
        if not confirm:
            messages.warning(request, '请确认您要清空所有AI习题')
            return redirect('courses:my_ai_exercises')
        
        # 获取当前用户的AI习题和答题记录数量
        exercise_count = AIGeneratedExercise.objects.filter(user=request.user).count()
        attempt_count = AIExerciseAttempt.objects.filter(user=request.user).count()
        
        # 删除当前用户的答题记录
        AIExerciseAttempt.objects.filter(user=request.user).delete()
        
        # 删除当前用户的习题
        AIGeneratedExercise.objects.filter(user=request.user).delete()
        
        messages.success(request, f'已清空您的AI习题库，删除了 {exercise_count} 道习题和 {attempt_count} 条答题记录')
        
        return redirect('courses:my_ai_exercises')
    
    return redirect('courses:my_ai_exercises')

@csrf_exempt  # 临时添加CSRF豁免
@require_http_methods(["POST"])
def submit_exercise_feedback(request):
    """处理习题反馈提交"""
    try:
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        
        if not exercise_id:
            return JsonResponse({'status': 'error', 'error': '缺少习题ID'})
        
        # 获取习题对象
        try:
            exercise = Exercise.objects.get(id=exercise_id)
        except Exercise.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': '习题不存在'})
        
        # 获取问题类型列表
        problem_types = data.get('problem_types', [])
        if not problem_types:
            return JsonResponse({'status': 'error', 'error': '请至少选择一种问题类型'})
        
        # 创建反馈记录
        feedback = ExerciseFeedback.objects.create(
            user=request.user if request.user.is_authenticated else None,
            exercise=exercise,
            book_title=data.get('book_title', ''),
            chapter_number=data.get('chapter_number', ''),
            section_number=data.get('section_number', ''),
            section_title=data.get('section_title', ''),
            problem_types=problem_types,
            details=data.get('details', '')
        )
        
        # 记录日志
        logger.info(f"用户提交了习题反馈: ID={feedback.id}, 习题ID={exercise_id}, 问题类型={problem_types}")
        
        return JsonResponse({'status': 'success', 'message': '反馈提交成功'})
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': '无效的JSON数据'})
    except Exception as e:
        logger.error(f"处理习题反馈时出错: {str(e)}")
        return JsonResponse({'status': 'error', 'error': f'服务器错误: {str(e)}'})

@require_POST
@csrf_exempt
async def ai_grade_comprehensive(request):
    """
    使用大模型API为综合题提供评分 (异步版本)
    """
    try:
        # 解析请求数据
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        user_answer = data.get('user_answer')
        model_type = data.get('model_type', 'grok')  # 默认使用Grok模型
        
        # 参数验证
        if not exercise_id or not user_answer:
            return JsonResponse({
                'status': 'error',
                'error': '缺少必要参数'
            })
        
        # 获取习题
        try:
            exercise = await sync_to_async(Exercise.objects.get)(id=exercise_id)
        except Exercise.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': '习题不存在'
            })
        
        # 确保是综合题
        if exercise.type != 'comprehensive':
            return JsonResponse({
                'status': 'error',
                'error': '该习题不是综合题'
            })
            
        # 获取正确答案和问题内容
        correct_answer = exercise.explanation or "未提供标准答案"
        question_content = exercise.content
        
        try:
            # 调用大模型API进行评分
            score, feedback = await call_llm_api_for_grading_async(question_content, correct_answer, user_answer, model_type)
            
            # 使用sync_to_async正确检查用户认证状态
            is_authenticated = False
            try:
                is_authenticated = await sync_to_async(lambda: request.user.is_authenticated)()
            except Exception as auth_error:
                logger.warning(f"检查用户认证状态失败: {str(auth_error)}")
            
            # 如果用户已登录，保存做题记录
            if is_authenticated:
                try:
                    # 创建尝试记录
                    await sync_to_async(ExerciseAttempt.objects.create)(
                        user=request.user,
                        exercise=exercise,
                        user_answer=user_answer,
                        is_correct=score >= 7  # 如果得分达到7分以上，认为基本正确
                    )
                except Exception as db_error:
                    # 记录错误但继续处理，不影响评分结果返回
                    logger.error(f"保存答题记录失败: {str(db_error)}")
            
            # 返回评分结果
            return JsonResponse({
                'status': 'success',
                'score': score,
                'feedback': feedback,
                'correct_answer': md_convert(correct_answer),
                'model_used': model_type
            })
        except ValueError as e:
            # 大模型API调用错误
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'error': 'JSON格式错误'
        })
    except Exception as e:
        logger.error(f"AI评分错误: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'error': f"服务器错误: {str(e)}"
        })

async def call_llm_api_for_grading_async(question, correct_answer, user_answer, model_type='grok'):
    """
    异步调用大模型API进行评分
    
    参数:
    - question: 问题内容
    - correct_answer: 正确答案
    - user_answer: 用户答案
    - model_type: 模型类型，默认为'grok'
    
    返回:
    - score: 分数 (0-10)
    - feedback: 评价反馈
    """
    try:
        # 根据指定模型类型选择API
        if model_type == 'grok':
            api_key = "xai-5VGZ4fJ6XxLxQ6y5yIgwGxa8sUwUv23UszOulhIUJeSPAsXENcTs8wTZiZ8bbRJYWc7T5SNBzJ5sMMMT"
            api_url = "https://api.x.ai/v1/chat/completions"
            model_name = "grok-3-fast-beta"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一名专业评分员，请对学生的计算机学科习题答案进行评分。"
                    },
                    {
                        "role": "user",
                        "content": get_grading_prompt(question, correct_answer, user_answer)
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
        else:  # 使用deepseek或其他模型
            api_key = "sk-0a05970e93264dffa93f31f9916245a7"   
            api_url = "https://api.deepseek.com/chat/completions"
            model_name = "deepseek-chat"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": get_grading_prompt(question, correct_answer, user_answer)
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
        
        # 检查API密钥是否配置
        if not api_key:
            logger.error(f"未配置{model_type.upper()}API密钥")
            raise ValueError(f"未配置{model_type.upper()}API密钥，请联系管理员")
        
        # 使用单独的错误处理函数包装API调用
        return await safe_api_call(api_url, headers, payload, model_type)
                
    except asyncio.TimeoutError:
        error_msg = f"{model_type.upper()}API调用超时"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"调用{model_type.upper()}API错误: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise ValueError(error_msg)

async def safe_api_call(api_url, headers, payload, model_type):
    """
    安全的API调用封装，处理多种可能的错误情况
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60  # 60秒超时
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # 解析回复，处理不同API的响应格式
                    if model_type == 'grok':
                        ai_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    else:  # deepseek
                        ai_response = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    logger.info(f"获取到{model_type.upper()}模型回复: {ai_response[:100]}...")
                    
                    # 解析AI回复中的分数
                    score_match = re.search(r'分数[:：]\s*(\d+)', ai_response)
                    if score_match:
                        score = int(score_match.group(1))
                        # 确保分数在0-10范围内
                        score = max(0, min(score, 10))
                    else:
                        # 如果找不到明确的分数标记，尝试其他可能的格式
                        # 尝试查找独立的数字（通常是分数）
                        alt_score_match = re.search(r'[^\d](\d{1,2})[^\d]', ai_response)
                        if alt_score_match:
                            potential_score = int(alt_score_match.group(1))
                            # 只接受0-10范围内的数字作为分数
                            if 0 <= potential_score <= 10:
                                score = potential_score
                            else:
                                score = 5  # 默认中等分数
                        else:
                            # 如果仍然找不到，基于文本内容估计分数
                            if any(word in ai_response.lower() for word in ['优秀', '完美', '出色', '非常好']):
                                score = 9
                            elif any(word in ai_response.lower() for word in ['良好', '基本正确', '好']):
                                score = 7
                            elif any(word in ai_response.lower() for word in ['一般', '部分正确', '不完整']):
                                score = 5
                            else:
                                score = 5  # 默认中等分数
                    
                    # 去除分数部分，保留评价
                    feedback = re.sub(r'分数[:：]\s*\d+', '', ai_response).strip()
                    
                    # 如果反馈内容太短，可能是解析出了问题，保留原始回复
                    if len(feedback) < 20:
                        feedback = ai_response
                    
                    return score, md_convert(feedback)
                else:
                    # API调用失败
                    response_text = await response.text()
                    error_msg = f"{model_type.upper()}API调用失败: HTTP {response.status} - {response_text}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
    except aiohttp.ClientError as e:
        raise ValueError(f"{model_type.upper()}API连接错误: {str(e)}")
    except Exception as e:
        raise ValueError(f"{model_type.upper()}API处理错误: {str(e)}")

def get_grading_prompt(question, correct_answer, user_answer):
    """
    生成评分提示词
    """
    return f"""
作为一名专业评分员，请对以下计算机学科习题的回答进行评分。

## 问题:
{question}

## 标准答案:
{correct_answer}

## 学生答案:
{user_answer}

请根据学生答案与标准答案的匹配程度，为学生的回答评分(0-10分)，并提供详细的评分解释。

请严格按照以下格式返回：
1. 第一行必须包含"分数：X"，其中X为0到10的整数
2. 然后空一行
3. 接下来是评价内容，详细分析学生答案与标准答案的差异和优缺点

判分标准：
- 0-3分：答案与标准答案相差很大，缺少关键概念或核心要点
- 4-6分：答案包含部分关键概念，但不完整或有一些错误
- 7-8分：答案基本正确，包含大部分关键概念，可能有小错误或不够全面
- 9-10分：答案非常完善，涵盖所有关键概念，表述准确清晰

请务必客观公正地评分，不要过于严格或宽松。
"""

def knowledge_graph(request):
    """展示知识图谱页面"""
    books = Book.objects.all()[:4]  # 获取前4本书
    
    # 准备数据格式
    graph_data = {
        "center": {"id": "center", "name": "知识体系", "type": "center"},
        "books": [],
    }
    
    for book in books:
        book_node = {"id": f"book_{book.id}", "name": book.title, "type": "book"}
        chapters = []
        
        for chapter in book.chapters.all():
            chapter_node = {"id": f"chapter_{chapter.id}", "name": f"第{chapter.number}章 {chapter.title}", "type": "chapter"}
            sections = []
            
            # 过滤掉"章节介绍"类型的小节
            for section in chapter.sections.exclude(section_type='introduction'):
                # 也可以根据标题过滤: chapter.sections.exclude(title__contains='介绍')
                section_node = {"id": f"section_{section.id}", "name": f"{section.number} {section.title}", "type": "section"}
                sections.append(section_node)
            
            # 只有当章节下有有效小节时才添加章节节点
            if sections:
                chapter_node["children"] = sections
                chapters.append(chapter_node)
        
        # 只有当书下有有效章节时才添加书籍节点
        if chapters:
            book_node["children"] = chapters
            graph_data["books"].append(book_node)
    
    context = {
        'graph_data': graph_data,
    }
    
    return render(request, 'courses/knowledge_graph.html', context)
