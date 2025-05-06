import json
import requests
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt  # 添加CSRF豁免装饰器
# 确保导入所有需要的模型
from .models import Book, Chapter, Section, Exercise, Knowledge, UserMistakeCollection, ExerciseKnowledge, ExerciseAttempt, AIGeneratedExercise, AIExerciseAttempt
from django.db.models import Count, Q, F, Sum, Case, When, Value, IntegerField
from django.utils import timezone
import markdown
# 确保 User 模型在模型文件中已导入，或者在这里导入
# from django.contrib.auth.models import User
import logging
import time

# 替换配置
# Grok API配置
GROK_API_KEY = "xai-O3QdRmxwS48SZJGgp646FnBoFyum2liAKZTEim1frYcTf8Uv6BuNcDsjLbgDGIIPlrQhotNKKGzCs8qQ"  # 实际使用时需要填入您的API密钥
GROK_API_URL = " https://api.x.ai/v1/chat/completions"  # 假设的API URL

# DeepSeek API配置
DEEPSEEK_API_KEY = "sk-f2d0085bbb88479b9b0d7b1f2451b310"  # 实际使用时需要填入您的API密钥
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"  # 假设的API URL

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

@login_required
@require_POST
def get_ai_exercise_recommendations(request):
    """处理AI推荐请求并返回结果"""
    try:
        model_type = request.POST.get('model_type', CURRENT_MODEL)
        logger.info(f"收到推荐请求，模型类型: {model_type}")
        
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
        raw_recommendations = _call_large_language_model_with_retry(prompt, model_type)
        
        # 记录原始返回
        logger.info(f"API原始返回: {json.dumps(raw_recommendations, ensure_ascii=False)}")
        
        # 后处理推荐结果，确保格式正确
        recommendations = _post_process_recommendations(raw_recommendations)
        
        # 记录处理后的结果
        logger.info(f"处理后的结果: {json.dumps(recommendations, ensure_ascii=False)}")
        
        # 最后安全检查，确保每个推荐题目至少有options字段
        for item in recommendations:
            if isinstance(item, dict) and 'type' in item:
                if item['type'] in ['单选题', '多选题'] and ('options' not in item or not item['options']):
                    logger.warning(f"推荐题目缺少options字段: {json.dumps(item, ensure_ascii=False)}")
                    # 确保添加默认选项
                    item['options'] = {
                        'A': '选项A (系统生成)',
                        'B': '选项B (系统生成)',
                        'C': '选项C (系统生成)',
                        'D': '选项D (系统生成)'
                    }
        
        # 将推荐结果保存到数据库
        saved_recommendations = []
        for item in recommendations:
            if isinstance(item, dict) and 'content' in item and not 'error' in item:
                # 将题目类型转换为数据库格式
                exercise_type = 'single'  # 默认为单选题
                if item.get('type') == '多选题':
                    exercise_type = 'multiple'
                elif item.get('type') == '综合题':
                    exercise_type = 'comprehensive'
                
                # 处理难度
                difficulty = 'medium'  # 默认为中等
                if item.get('difficulty') == '简单':
                    difficulty = 'easy'
                elif item.get('difficulty') == '困难':
                    difficulty = 'hard'
                
                # 处理知识点
                knowledge_points = item.get('knowledge_points', [])
                if isinstance(knowledge_points, str):
                    knowledge_points = [knowledge_points]
                
                # 创建或更新AI习题记录
                ai_exercise, created = AIGeneratedExercise.objects.update_or_create(
                    user=request.user,
                    content=item['content'],
                    defaults={
                        'model_type': model_type,
                        'type': exercise_type,
                        'options': item.get('options'),
                        'answer': item.get('answer', ''),
                        'explanation': item.get('explanation', '无解析'),
                        'difficulty': difficulty,
                        'knowledge_points': knowledge_points,
                        'reason': item.get('reason', '基于您的学习情况推荐')
                    }
                )
                
                # 将数据库ID添加到推荐结果
                item['db_id'] = ai_exercise.id
                saved_recommendations.append(ai_exercise)
        
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
        logger.error(f"生成推荐时出错: {str(e)}", exc_info=True)
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
对于选择题，必须提供选项和正确答案；对于所有题目，必须提供详细解析。

每个推荐的题目应包含：
1. content: 题目内容
2. type: 题目类型（单选题/多选题/综合题）
3. difficulty: 难度级别（简单/中等/困难）
4. options: 若为选择题，提供A、B、C、D选项及其内容
5. answer: 正确答案（单选题为A/B/C/D之一，多选题为逗号分隔的选项，如"A,C"）
6. explanation: 详细解析
7. knowledge_points: 相关知识点列表
8. reason: 推荐理由

请以JSON格式返回，格式如下:
[
  {{
    "content": "题目内容",
    "type": "题目类型",
    "difficulty": "难度级别",
    "options": {{
      "A": "选项A内容",
      "B": "选项B内容",
      "C": "选项C内容",
      "D": "选项D内容"
    }},
    "answer": "正确答案",
    "explanation": "详细解析",
    "knowledge_points": ["知识点1", "知识点2"],
    "reason": "推荐理由"
  }},
  ...
]

注意：确保所有选择题都提供完整的选项内容，以及正确的答案和解析。
"""
    return prompt

def _call_large_language_model_with_retry(prompt, model_type="grok", max_retries=3, timeout=60):
    """带有重试机制的大语言模型API调用函数
    
    Args:
        prompt: 提示词
        model_type: 模型类型，"grok"或"deepseek"
        max_retries: 最大重试次数
        timeout: 请求超时时间（秒）
    
    Returns:
        list: 处理后的模型响应
    """
    logger.info(f"开始调用{model_type}模型API（带重试机制），最大重试次数：{max_retries}，超时：{timeout}秒")
    
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
    
    while retry_count < max_retries:
        try:
            # 根据模型类型选择不同的API调用函数
            if model_type == "grok":
                logger.info(f"尝试调用Grok API（尝试 {retry_count + 1}/{max_retries}）")
                # 选择要使用的API函数
                api_func = _call_grok_api
                api_url = GROK_API_URL
            else:  # deepseek
                logger.info(f"尝试调用DeepSeek API（尝试 {retry_count + 1}/{max_retries}）")
                api_func = _call_deepseek_api
                api_url = DEEPSEEK_API_URL
            
            # 发送请求前检查API端点是否可达
            try:
                # 使用HEAD请求快速检查API端点是否可达
                head_response = requests.head(api_url, timeout=5)
                logger.info(f"{model_type} API端点状态码: {head_response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"{model_type} API端点不可达: {str(e)}")
                # 如果端点不可达，直接进入下一次重试
                retry_count += 1
                last_error = f"API端点不可达: {str(e)}"
                
                if retry_count < max_retries:
                    logger.info(f"等待2秒后重试...")
                    time.sleep(2)
                continue
            
            # 调用相应的API函数，设置更长的超时时间
            response = api_func(prompt)
            
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
                    time.sleep(2)
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
                time.sleep(wait_time)
    
    # 如果所有重试都失败，返回错误信息
    logger.error(f"{model_type} API在{max_retries}次尝试后仍然失败: {last_error}")
    return [{"error": f"API调用在{max_retries}次尝试后失败: {last_error}", "content": "模型调用失败，请稍后再试。"}]

def _call_grok_api(prompt):
    """调用Grok API"""
    logger.info("正在调用Grok API...")
    
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
        response = requests.post(GROK_API_URL, headers=headers, json=data, timeout=60)
        
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

# def _mock_ai_recommendations(model_type="grok"):
#     """提供模拟的AI推荐数据（开发/测试环境使用）"""
#     # 根据不同模型提供略有差异的模拟数据，便于区分
#     common_recommendations = [
#         {
#             "content": "设计一个算法，实现链表的反转操作。要求时间复杂度为O(n)，空间复杂度为O(1)。",
#             "type": "综合题",
#             "difficulty": "中等",
#             "knowledge_points": ["链表", "指针操作", "算法复杂度"],
#             "reason": "学生在链表操作相关题目上存在困难，这道题可以帮助巩固链表基本操作和指针概念。"
#         },
#         {
#             "content": "请分析快速排序算法的平均时间复杂度和最坏时间复杂度，并解释为什么存在差异。",
#             "type": "综合题",
#             "difficulty": "中等",
#             "knowledge_points": ["排序算法", "算法复杂度分析", "分治策略"],
#             "reason": "学生在算法复杂度分析方面有欠缺，这道题有助于加深对复杂度分析的理解。"
#         },
#         {
#             "content": "以下哪种数据结构适合实现优先队列？\nA. 数组\nB. 链表\nC. 堆\nD. 栈",
#             "type": "单选题",
#             "difficulty": "简单",
#             "knowledge_points": ["数据结构", "优先队列", "堆"],
#             "reason": "学生在数据结构选择题上有失误，这道题可以帮助理解不同数据结构的应用场景。"
#         }
#     ]
    
#     if model_type == "grok":
#         grok_specific = [
#             {
#                 "content": "给定一棵二叉树，编写算法求树的最大深度。",
#                 "type": "综合题",
#                 "difficulty": "简单",
#                 "knowledge_points": ["二叉树", "递归", "深度优先搜索"],
#                 "reason": "学生在树相关算法上存在困难，这道基础题有助于巩固树的遍历和递归概念。"
#             },
#             {
#                 "content": "以下关于哈希表的描述，正确的是：\nA. 哈希表的插入和查找操作平均时间复杂度为O(n)\nB. 哈希表不存在冲突问题\nC. 哈希表的负载因子不影响性能\nD. 哈希表的平均查找时间复杂度为O(1)",
#                 "type": "单选题",
#                 "difficulty": "中等",
#                 "knowledge_points": ["哈希表", "数据结构", "算法复杂度"],
#                 "reason": "学生对数据结构的性能特性理解不足，这道题可以帮助加深对哈希表性能特点的理解。"
#             }
#         ]
#         return common_recommendations + grok_specific
#     else:  # deepseek
#         deepseek_specific = [
#             {
#                 "content": "实现一个算法解决背包问题（Knapsack Problem），给定n个物品，每个物品有重量和价值，在总重量不超过W的情况下，如何选择物品使总价值最大？",
#                 "type": "综合题",
#                 "difficulty": "困难",
#                 "knowledge_points": ["动态规划", "贪心算法", "背包问题"],
#                 "reason": "学生在算法设计类问题上表现较弱，这道题可以培养系统性解决复杂问题的能力。"
#             },
#             {
#                 "content": "下列关于B树和B+树的说法，错误的是：\nA. B+树只在叶子节点存储数据\nB. B树适合做文件系统\nC. B+树的查询稳定性优于B树\nD. B树比B+树支持更高效的范围查询",
#                 "type": "单选题",
#                 "difficulty": "中等",
#                 "knowledge_points": ["树结构", "数据库索引", "查询优化"],
#                 "reason": "学生对高级数据结构理解不足，这道题有助于理解不同树结构的应用场景和优缺点。"
#             }
#         ]
#         return common_recommendations + deepseek_specific

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
                generated_exercises = _generate_exercises_from_knowledge(selected_knowledge, request.user)
                
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
        extracted_knowledge = _call_large_language_model_with_retry(prompt, CURRENT_MODEL)
        return extracted_knowledge
    except Exception as e:
        logger.error(f"调用大模型提取知识点时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []

def _generate_exercises_from_knowledge(knowledge_points, user=None):
    """根据知识点生成相关练习题，并保存到数据库"""
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
        generated_exercises = _call_large_language_model_with_retry(prompt, CURRENT_MODEL)
        
        # 如果提供了用户，则将生成的习题保存到数据库
        if user and isinstance(generated_exercises, list):
            saved_exercises = []
            for item in generated_exercises:
                if isinstance(item, dict) and 'content' in item:
                    # 确定题目类型
                    exercise_type = 'single'
                    if item.get('type') == '多选题' or item.get('type') == 'multiple':
                        exercise_type = 'multiple'
                    elif item.get('type') == '综合题':
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
                    
                    # 保存到数据库
                    ai_exercise = AIGeneratedExercise.objects.create(
                        user=user,
                        model_type='knowledge_extraction',  # 标记来源
                        type=exercise_type,
                        content=item['content'],
                        options=item.get('options', {}),
                        answer=item.get('answer', ''),
                        explanation=item.get('explanation', ''),
                        knowledge_points=knowledge_points_list,
                        reason='基于知识点提取生成',
                        difficulty='medium'  # 默认中等难度
                    )
                    
                    # 添加数据库ID到返回的习题中，以便前端使用
                    item['db_id'] = ai_exercise.id
                    saved_exercises.append(ai_exercise)
            
            logger.info(f"已成功保存 {len(saved_exercises)} 道习题到数据库")
        
        return generated_exercises
    except Exception as e:
        logger.error(f"调用大模型生成练习题时出错: {str(e)}")
        # 如果API调用失败，返回空列表
        return []

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
                processed_item['type'] = '多选题'
            elif is_single_choice or has_options:
                processed_item['type'] = '单选题'
            else:
                processed_item['type'] = '综合题'
        
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
            if options or processed_item['type'] in ['单选题', '多选题']:
                # 如果没有足够的选项（至少有四个ABCD），补充默认选项
                for key in ['A', 'B', 'C', 'D']:
                    if key not in options:
                        options[key] = f'选项{key}'
                
                processed_item['options'] = options
        
        # 确保答案格式正确
        if 'answer' not in processed_item or not processed_item['answer']:
            if processed_item['type'] == '单选题':
                processed_item['answer'] = 'A'  # 默认答案
            elif processed_item['type'] == '多选题':
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
def submit_ai_exercise_attempt(request):
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
            exercise = AIGeneratedExercise.objects.get(id=exercise_id, user=request.user)
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
        attempt = AIExerciseAttempt.objects.create(
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
def get_ai_exercise_detail(request, exercise_id):
    """获取AI生成习题的详细信息"""
    try:
        # 获取习题信息
        exercise = AIGeneratedExercise.objects.get(id=exercise_id, user=request.user)
        
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

def _call_large_language_model(prompt, model_type="grok"):
    """调用大语言模型API获取推荐（兼容性函数，内部使用重试机制）"""
    # 使用实际API
    logger.info(f"使用{model_type} API生成回答")
    if model_type == "grok":
        # 调用带重试机制的函数
        return _call_large_language_model_with_retry(prompt, model_type)
    elif model_type == "deepseek":
        # 调用带重试机制的函数
        return _call_large_language_model_with_retry(prompt, model_type)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

@login_required
def my_ai_exercises(request):
    """用户的AI习题库 - 显示所有AI生成的习题"""
    # 获取当前用户的所有AI生成习题
    ai_exercises = AIGeneratedExercise.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # 按来源/模型类型分组
    by_model = {}
    for exercise in ai_exercises:
        model_type = exercise.model_type
        if model_type not in by_model:
            by_model[model_type] = []
        by_model[model_type].append(exercise)
    
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
    
    context = {
        'ai_exercises': ai_exercises,
        'by_model': by_model,
        'attempts_by_exercise': attempts_by_exercise,
        'total_count': ai_exercises.count()
    }
    
    return render(request, 'courses/my_ai_exercises.html', context)