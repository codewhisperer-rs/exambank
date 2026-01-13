import logging
import asyncio
from django.core.management.base import BaseCommand
from courses.models import AIGeneratedExercise, AIExerciseAttempt
from asgiref.sync_to_async import sync_to_async

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清空AI习题数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认清空数据库'
        )

    async def handle_async(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('警告: 此操作将永久删除所有AI生成的习题及相关答题记录!'))
            self.stdout.write('如果确定要执行清空操作，请添加 --confirm 参数')
            return

        # 获取记录数量（异步方式）
        get_attempt_count = sync_to_async(AIExerciseAttempt.objects.count)
        get_exercise_count = sync_to_async(AIGeneratedExercise.objects.count)
        
        attempt_count = await get_attempt_count()
        exercise_count = await get_exercise_count()
        
        # 先删除答题记录（异步方式）
        delete_attempts = sync_to_async(lambda: AIExerciseAttempt.objects.all().delete())
        await delete_attempts()
        
        # 然后删除习题（异步方式）
        delete_exercises = sync_to_async(lambda: AIGeneratedExercise.objects.all().delete())
        await delete_exercises()
        
        self.stdout.write(self.style.SUCCESS(f'数据库清空完成!'))
        self.stdout.write(self.style.SUCCESS(f'已删除 {exercise_count} 道AI习题和 {attempt_count} 条答题记录'))
        
    def handle(self, *args, **options):
        """
        作为入口点的同步方法，调用异步的handle方法
        """
        asyncio.run(self.handle_async(*args, **options)) 