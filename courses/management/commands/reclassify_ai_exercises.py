import json
import logging
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from courses.models import AIGeneratedExercise, Book
from courses.views import _call_large_language_model_with_retry
from asgiref.sync_to_async import sync_to_async

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '重新分类现有的AI习题，根据题目内容判断其所属书籍'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            default=10,
            help='每次处理的习题数量'
        )
        parser.add_argument(
            '--model',
            type=str,
            default='grok',
            help='使用的AI模型类型 (grok 或 deepseek)'
        )

    async def handle_async(self, *args, **options):
        batch_size = options['batch']
        model_type = options['model']
        
        # 获取所有未关联书籍的AI习题
        get_unclassified_exercises = sync_to_async(
            lambda: list(AIGeneratedExercise.objects.filter(book__isnull=True))
        )
        get_unclassified_count = sync_to_async(
            lambda: AIGeneratedExercise.objects.filter(book__isnull=True).count()
        )
        
        unclassified_exercises = await get_unclassified_exercises()
        total_count = await get_unclassified_count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('没有需要分类的习题'))
            return
        
        self.stdout.write(f'开始处理 {total_count} 道未分类的习题...')
        
        # 获取所有书籍
        get_books = sync_to_async(lambda: list(Book.objects.all()))
        books = await get_books()
        
        book_list = [{'id': book.id, 'title': book.title} for book in books]
        books_dict = {book.title: book for book in books}
        
        # 按批次处理
        for i in range(0, total_count, batch_size):
            batch = unclassified_exercises[i:i+batch_size]
            exercises_data = []
            
            for ex in batch:
                exercises_data.append({
                    'id': ex.id,
                    'content': ex.content,
                    'type': dict(AIGeneratedExercise.TYPES).get(ex.type, '未知'),
                    'knowledge_points': ex.knowledge_points
                })
            
            # 构建提示词
            prompt = f"""
你是一个教育分类专家，擅长将教育内容按学科分类。请帮助我确定以下习题分别属于哪本教材。

可用的书籍列表:
{json.dumps(book_list, ensure_ascii=False, indent=2)}

要分类的习题:
{json.dumps(exercises_data, ensure_ascii=False, indent=2)}

请仔细分析每道习题的内容和知识点，确定它最适合哪本书。
返回JSON格式如下:
[
  {{
    "id": 习题ID,
    "book_title": "所属书籍标题",
    "confidence": 0-100的置信度数值,
    "reason": "简短解释为什么这道题属于该书籍"
  }},
  ...
]
"""
            
            try:
                # 调用AI模型进行分类 (假设_call_large_language_model_with_retry是同步函数)
                call_llm = sync_to_async(
                    lambda p, m: _call_large_language_model_with_retry(p, m)
                )
                classifications = await call_llm(prompt, model_type)
                
                # 应用分类结果
                updated_count = 0
                for result in classifications:
                    if isinstance(result, dict) and 'id' in result and 'book_title' in result:
                        exercise_id = result['id']
                        book_title = result['book_title']
                        
                        if book_title in books_dict:
                            try:
                                # 获取习题并更新
                                get_exercise = sync_to_async(
                                    lambda: AIGeneratedExercise.objects.get(id=exercise_id)
                                )
                                
                                try:
                                    exercise = await get_exercise()
                                    exercise.book = books_dict[book_title]
                                    
                                    # 保存更新
                                    save_exercise = sync_to_async(exercise.save)
                                    await save_exercise()
                                    
                                    updated_count += 1
                                    self.stdout.write(f'习题 ID {exercise_id} 已归类到 "{book_title}" (置信度: {result.get("confidence", "未知")})')
                                except AIGeneratedExercise.DoesNotExist:
                                    self.stdout.write(self.style.WARNING(f'习题 ID {exercise_id} 不存在'))
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'更新习题 ID {exercise_id} 时出错: {str(e)}'))
                        else:
                            self.stdout.write(self.style.WARNING(f'书籍 "{book_title}" 不存在于数据库中'))
                
                self.stdout.write(self.style.SUCCESS(f'批次完成: {updated_count}/{len(batch)} 道习题已更新'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'处理批次时出错: {str(e)}'))
        
        # 显示最终结果
        get_remaining = sync_to_async(
            lambda: AIGeneratedExercise.objects.filter(book__isnull=True).count()
        )
        remaining = await get_remaining()
        classified = total_count - remaining
        
        self.stdout.write(self.style.SUCCESS(f'分类完成: {classified}/{total_count} 道习题已关联到书籍'))
        if remaining > 0:
            self.stdout.write(self.style.WARNING(f'仍有 {remaining} 道习题未分类'))
            
    def handle(self, *args, **options):
        """
        作为入口点的同步方法，调用异步的handle方法
        """
        asyncio.run(self.handle_async(*args, **options)) 