import logging
from django.core.management.base import BaseCommand
from courses.models import AIGeneratedExercise, AIExerciseAttempt

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '清空AI习题数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认清空数据库'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('警告: 此操作将永久删除所有AI生成的习题及相关答题记录!'))
            self.stdout.write('如果确定要执行清空操作，请添加 --confirm 参数')
            return

        # 先删除答题记录
        attempt_count = AIExerciseAttempt.objects.count()
        AIExerciseAttempt.objects.all().delete()
        
        # 然后删除习题
        exercise_count = AIGeneratedExercise.objects.count()
        AIGeneratedExercise.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(f'数据库清空完成!'))
        self.stdout.write(self.style.SUCCESS(f'已删除 {exercise_count} 道AI习题和 {attempt_count} 条答题记录')) 