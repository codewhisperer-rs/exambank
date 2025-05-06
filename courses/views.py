import json
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt  # 添加CSRF豁免装饰器
# 确保导入所有需要的模型
from .models import Book, Chapter, Section, Exercise, Knowledge, UserMistakeCollection, ExerciseKnowledge, ExerciseAttempt
from django.db.models import Count, Q, F, Sum, Case, When, Value, IntegerField
from django.utils import timezone
import markdown
# 确保 User 模型在模型文件中已导入，或者在这里导入
# from django.contrib.auth.models import User
import logging

# 替换配置
# Grok API配置
GROK_API_KEY = "xai-O3QdRmxwS48SZJGgp646FnBoFyum2liAKZTEim1frYcTf8Uv6BuNcDsjLbgDGIIPlrQhotNKKGzCs8qQ"  # 实际使用时需要填入您的API密钥
GROK_API_URL = " https://api.x.ai/v1/chat/completions"  # 假设的API URL

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-f2d0085bbb88479b9b0d7b1f2451b310"  # 实际使用时需要填入您的API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # 假设的API URL

# 当前使用的模型类型，可以是 "grok" 或 "deepseek"
CURRENT_MODEL = "grok-3-latest"  # 默认使用Grok

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
            'pymdownx.arithmatex'  # 添加对 LaTeX 公式的支持
        ], extension_configs={
            'pymdownx.arithmatex': {
                'generic': True  # 使用通用的 MathJax 配置
            }
        })
        
        content = md.convert(exercise.content)
        explanation = md.convert(exercise.explanation) if exercise.explanation else ''
        
        # 获取用户在错题集中的记录
        user_mistake = None
        user_answer = None
        try:
            # 查找该用户对这个习题的错题记录
            user_mistake = UserMistakeCollection.objects.get(
                user=request.user,
                exercise=exercise
            )
            
            # 优先使用错题集中保存的最近错误答案
            if user_mistake.last_wrong_answer:
                user_answer = user_mistake.last_wrong_answer
            else:
                # 如果没有保存最近错误答案，则查找最近一次的错误尝试
                latest_attempt = ExerciseAttempt.objects.filter(
                    user=request.user,
                    exercise=exercise,
                    is_correct=False  # 只查找错误的尝试
                ).order_by('-attempt_time').first()
                
                if latest_attempt:
                    user_answer = latest_attempt.user_answer
        except UserMistakeCollection.DoesNotExist:
            pass
        
        # 获取选项信息
        options_dict = {}
        if exercise.options and isinstance(exercise.options, dict):
            options_dict = exercise.options
        
        # 构建选项的HTML表示
        options_html = ''
        for key, value in options_dict.items():
            options_html += f'<div class="option"><strong>{key}.</strong> {value}</div>'
        
        # 完整的内容
        full_content = f"{content}<div class='exercise-options mt-3'>{options_html}</div>"
        
        response_data = {
            'id': exercise.id,
            'type': exercise.type,
            'type_display': exercise.get_type_display(),
            'content': full_content,
            'options': options_dict,  # 添加原始选项数据
            'answer': exercise.answer,
            'user_answer': user_answer,  # 添加用户答案
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

@login_required
@require_POST
def get_ai_exercise_recommendations(request):
    """处理AI推荐请求并返回结果"""
    try:
        model_type = request.POST.get('model_type', CURRENT_MODEL)
        print(f"收到推荐请求，模型类型: {model_type}")
        
        # 确保模型类型有效
        if model_type not in ['grok', 'deepseek']:
            model_type = CURRENT_MODEL
        
        # 获取用户错题记录
        mistake_collections = UserMistakeCollection.objects.filter(
            user=request.user
        ).select_related('exercise')[:5]
        
        if not mistake_collections.exists():
            context = {
                'error_message': '没有足够的错题记录进行个性化推荐',
                'mistakes': UserMistakeCollection.objects.filter(
                    user=request.user
                ).select_related(
                    'exercise', 'exercise__section', 'exercise__section__chapter'
                ).order_by('-added_at')[:10],
                'knowledge_stats': get_user_knowledge_weakness(request.user),
                'selected_model': model_type
            }
            return render(request, 'courses/ai_recommend.html', context)
        
        # 准备提示词
        prompt = _prepare_recommendation_prompt(request.user, mistake_collections)
        
        # 调用大模型获取推荐结果
        recommendations = _call_large_language_model(prompt, model_type)
        
        # 准备渲染上下文
        context = {
            'recommendations': recommendations,
            'model_used': model_type,
            'mistakes': mistake_collections,
            'knowledge_stats': get_user_knowledge_weakness(request.user),
            'selected_model': model_type
        }
        
        return render(request, 'courses/ai_recommend.html', context)
    except Exception as e:
        print(f"生成推荐时出错: {str(e)}")
        context = {
            'error_message': f'生成推荐时出错: {str(e)}',
            'mistakes': UserMistakeCollection.objects.filter(
                user=request.user
            ).select_related(
                'exercise', 'exercise__section', 'exercise__section__chapter'
            ).order_by('-added_at')[:10],
            'knowledge_stats': get_user_knowledge_weakness(request.user),
            'selected_model': model_type if 'model_type' in locals() else CURRENT_MODEL
        }
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
            'correct_count': mc.correct_count
        })
    
    # 构建提示词
    prompt = f"""
作为一个智能教育助手，请根据以下学生的错题记录，推荐5个适合该学生练习的题目。
每道题目应该与学生的错题相关，但不应过于简单或过于困难。

学生错题记录:
{json.dumps(exercises_info, ensure_ascii=False, indent=2)}

请根据以上错题记录，分析学生的知识点薄弱区域，并推荐5个适合的练习题。
每个推荐的题目应包含：
1. 题目内容
2. 题目类型（单选题/多选题/综合题）
3. 难度级别（简单/中等/困难）
4. 相关知识点
5. 推荐理由

请以JSON格式返回，格式如下:
[
  {{
    "content": "题目内容",
    "type": "题目类型",
    "difficulty": "难度级别",
    "knowledge_points": ["知识点1", "知识点2"],
    "reason": "推荐理由"
  }},
  ...
]
"""
    return prompt

def _call_large_language_model(prompt, model_type="grok"):
    """调用大语言模型API获取推荐"""
    # 如果API密钥为空，使用模拟数据（开发环境）
    if model_type == "grok" and not GROK_API_KEY:
        logger.warning("Grok API密钥未设置，使用模拟数据")
        return _mock_ai_recommendations(model_type)
    elif model_type == "deepseek" and not DEEPSEEK_API_KEY:
        logger.warning("DeepSeek API密钥未设置，使用模拟数据")
        return _mock_ai_recommendations(model_type)
    
    # 使用实际API
    logger.info(f"使用{model_type} API生成回答")
    if model_type == "grok":
        return _call_grok_api(prompt)
    elif model_type == "deepseek":
        return _call_deepseek_api(prompt)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

def _call_grok_api(prompt):
    """调用Grok API"""
    logger.info("正在调用Grok API...")
    
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-3-latest",
        "messages": [
            {"role": "system", "content": "你是一个专业的教育助手，帮助学生根据错题记录推荐适合的练习题。请始终以JSON格式回复，确保回复内容可以被json.loads()函数解析。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=data, timeout=30)
        
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
    except requests.exceptions.Timeout:
        logger.error("Grok API调用超时")
        return [{"error": "API调用超时"}]
    except Exception as e:
        logger.error(f"Grok API调用出错: {str(e)}")
        return [{"error": f"API调用异常: {str(e)}"}]

def _call_deepseek_api(prompt):
    """调用DeepSeek API"""
    logger.info("正在调用DeepSeek API...")
    
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
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        
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
    except requests.exceptions.Timeout:
        logger.error("DeepSeek API调用超时")
        return [{"error": "API调用超时"}]
    except Exception as e:
        logger.error(f"DeepSeek API调用出错: {str(e)}")
        return [{"error": f"API调用异常: {str(e)}"}]

def _mock_ai_recommendations(model_type="grok"):
    """提供模拟的AI推荐数据（开发/测试环境使用）"""
    # 根据不同模型提供略有差异的模拟数据，便于区分
    common_recommendations = [
        {
            "content": "设计一个算法，实现链表的反转操作。要求时间复杂度为O(n)，空间复杂度为O(1)。",
            "type": "综合题",
            "difficulty": "中等",
            "knowledge_points": ["链表", "指针操作", "算法复杂度"],
            "reason": "学生在链表操作相关题目上存在困难，这道题可以帮助巩固链表基本操作和指针概念。"
        },
        {
            "content": "请分析快速排序算法的平均时间复杂度和最坏时间复杂度，并解释为什么存在差异。",
            "type": "综合题",
            "difficulty": "中等",
            "knowledge_points": ["排序算法", "算法复杂度分析", "分治策略"],
            "reason": "学生在算法复杂度分析方面有欠缺，这道题有助于加深对复杂度分析的理解。"
        },
        {
            "content": "以下哪种数据结构适合实现优先队列？\nA. 数组\nB. 链表\nC. 堆\nD. 栈",
            "type": "单选题",
            "difficulty": "简单",
            "knowledge_points": ["数据结构", "优先队列", "堆"],
            "reason": "学生在数据结构选择题上有失误，这道题可以帮助理解不同数据结构的应用场景。"
        }
    ]
    
    if model_type == "grok":
        grok_specific = [
            {
                "content": "给定一棵二叉树，编写算法求树的最大深度。",
                "type": "综合题",
                "difficulty": "简单",
                "knowledge_points": ["二叉树", "递归", "深度优先搜索"],
                "reason": "学生在树相关算法上存在困难，这道基础题有助于巩固树的遍历和递归概念。"
            },
            {
                "content": "以下关于哈希表的描述，正确的是：\nA. 哈希表的插入和查找操作平均时间复杂度为O(n)\nB. 哈希表不存在冲突问题\nC. 哈希表的负载因子不影响性能\nD. 哈希表的平均查找时间复杂度为O(1)",
                "type": "单选题",
                "difficulty": "中等",
                "knowledge_points": ["哈希表", "数据结构", "算法复杂度"],
                "reason": "学生对数据结构的性能特性理解不足，这道题可以帮助加深对哈希表性能特点的理解。"
            }
        ]
        return common_recommendations + grok_specific
    else:  # deepseek
        deepseek_specific = [
            {
                "content": "实现一个算法解决背包问题（Knapsack Problem），给定n个物品，每个物品有重量和价值，在总重量不超过W的情况下，如何选择物品使总价值最大？",
                "type": "综合题",
                "difficulty": "困难",
                "knowledge_points": ["动态规划", "贪心算法", "背包问题"],
                "reason": "学生在算法设计类问题上表现较弱，这道题可以培养系统性解决复杂问题的能力。"
            },
            {
                "content": "下列关于B树和B+树的说法，错误的是：\nA. B+树只在叶子节点存储数据\nB. B树适合做文件系统\nC. B+树的查询稳定性优于B树\nD. B树比B+树支持更高效的范围查询",
                "type": "单选题",
                "difficulty": "中等",
                "knowledge_points": ["树结构", "数据库索引", "查询优化"],
                "reason": "学生对高级数据结构理解不足，这道题有助于理解不同树结构的应用场景和优缺点。"
            }
        ]
        return common_recommendations + deepseek_specific

@login_required
def extract_mistake_knowledge_points(request):
    """从用户错题中提取知识点并基于大模型生成相关练习题"""
    if request.method == 'GET':
        # 获取用户的错题集
        mistakes = UserMistakeCollection.objects.filter(
            user=request.user
        ).select_related(
            'exercise', 'exercise__section', 'exercise__section__chapter'
        ).order_by('-added_at')[:10]  # 最近10道错题
        
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
            
            # 获取用户的错题集
            mistakes = UserMistakeCollection.objects.filter(
                user=request.user
            ).select_related(
                'exercise', 'exercise__section', 'exercise__section__chapter'
            ).order_by('-added_at')[:10]  # 最近10道错题
            
            if action == 'extract_knowledge':
                # 提取知识点
                extracted_knowledge = _extract_knowledge_from_mistakes(mistakes)
                
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
                
                # 根据选择的知识点生成练习题
                generated_exercises = _generate_exercises_from_knowledge(selected_knowledge)
                
                # 提取所有错题的知识点
                extracted_knowledge = _extract_knowledge_from_mistakes(mistakes)
                
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

def _extract_knowledge_from_mistakes(mistakes):
    """使用大模型从错题中提取知识点"""
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
        extracted_knowledge = _call_large_language_model(prompt, CURRENT_MODEL)
        return extracted_knowledge
    except Exception as e:
        logger.error(f"调用大模型提取知识点时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []

def _generate_exercises_from_knowledge(knowledge_points):
    """根据知识点生成相关练习题"""
    if not knowledge_points:
        return []
    
    # 构建提示词
    prompt = f"""
根据以下知识点，生成相关的练习题：
{', '.join(knowledge_points)}

请为每个知识点生成1-2道练习题，包括题目内容、选项（如适用）和答案。
每道题应该清晰、具体，并能够有效测试对该知识点的理解。

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
    "knowledge_point": "相关知识点"
  }},
  ...
]
"""
    
    # 调用大模型API生成练习题
    try:
        # 使用当前设置的默认模型
        generated_exercises = _call_large_language_model(prompt, CURRENT_MODEL)
        return generated_exercises
    except Exception as e:
        logger.error(f"调用大模型生成练习题时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []