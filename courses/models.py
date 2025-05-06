from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Book(models.Model):
    title = models.CharField(max_length=100, verbose_name='书名')
    description = models.TextField(blank=True, verbose_name='描述')
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, verbose_name='封面图片')
    
    class Meta:
        verbose_name = '书籍'
        verbose_name_plural = verbose_name
        
    def __str__(self):
        return self.title

class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name='所属书籍')
    number = models.IntegerField(verbose_name='章节号')
    title = models.CharField(max_length=200, verbose_name='章节标题')
    introduction = models.TextField(blank=True, verbose_name='章节介绍')
    
    class Meta:
        verbose_name = '章节'
        verbose_name_plural = verbose_name
        ordering = ['number']
        
    def __str__(self):
        return f"{self.book.title} - 第{self.number}章 {self.title}"

class Section(models.Model):
    SECTION_TYPES = (
        ('content', '内容小节'),
        ('introduction', '章节介绍'),
        ('summary', '章节小结'),
        ('faq', '常见问题/疑难点'),
        ('other', '其他'),
    )
    
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='sections', verbose_name='所属章节')
    number = models.CharField(max_length=10, verbose_name='小节号')  # 如1.1, 1.2等
    title = models.CharField(max_length=200, verbose_name='小节标题')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, default='content', verbose_name='小节类型')
    content = models.TextField(blank=True, verbose_name='小节内容 (Markdown)')
    
    class Meta:
        verbose_name = '小节'
        verbose_name_plural = verbose_name
        ordering = ['number']
        
    def __str__(self):
        return f"{self.chapter.book.title} - {self.number} {self.title}"

class Knowledge(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='knowledge_points', verbose_name='所属小节')
    title = models.CharField(max_length=200, verbose_name='知识点标题')
    content = models.TextField(verbose_name='知识点内容')
    order = models.IntegerField(default=0, verbose_name='排序')
    
    class Meta:
        verbose_name = '知识点'
        verbose_name_plural = verbose_name
        ordering = ['order']
        
    def __str__(self):
        return f"{self.section} - {self.title}"

class Exercise(models.Model):
    TYPES = (
        ('single', '单项选择题'),
        ('multiple', '多项选择题'),
        ('comprehensive', '综合题'),
    )
    
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='exercises', verbose_name='所属小节')
    type = models.CharField(max_length=20, choices=TYPES, verbose_name='题目类型')
    number = models.CharField(max_length=10, verbose_name='题号')  # 如01, 02等
    content = models.TextField(verbose_name='题目内容')
    options = models.JSONField(null=True, blank=True, verbose_name='选项')  # 用于选择题的选项
    answer = models.CharField(max_length=200, verbose_name='答案')
    explanation = models.TextField(verbose_name='解析')
    order = models.IntegerField(default=0, verbose_name='排序')
    knowledge_points = models.ManyToManyField(Knowledge, through='ExerciseKnowledge', related_name='related_exercises', verbose_name='相关知识点')
    
    class Meta:
        verbose_name = '习题'
        verbose_name_plural = verbose_name
        ordering = ['order', 'number']
        
    def __str__(self):
        return f"{self.section} - 第{self.number}题"

class ExerciseKnowledge(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='exercise_knowledge_links', verbose_name='习题')
    knowledge = models.ForeignKey(Knowledge, on_delete=models.CASCADE, related_name='exercise_knowledge_links', verbose_name='知识点')
    relevance = models.IntegerField(default=5, verbose_name='相关性程度', help_text='1-10，数值越大表示相关性越强')
    
    class Meta:
        verbose_name = '习题-知识点关联'
        verbose_name_plural = verbose_name
        unique_together = ['exercise', 'knowledge']
        
    def __str__(self):
        return f"{self.exercise} - {self.knowledge}"

class UserExerciseAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_attempts', verbose_name='用户')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='attempts', verbose_name='习题')
    is_correct = models.BooleanField(default=False, verbose_name='是否正确')
    user_answer = models.TextField(blank=True, null=True, verbose_name='用户答案') # 允许为空
    attempted_at = models.DateTimeField(auto_now_add=True, verbose_name='尝试时间') # 自动记录创建时间

    class Meta:
        verbose_name = '用户答题记录'
        verbose_name_plural = verbose_name
        ordering = ['-attempted_at'] # 通常按最近尝试排序

    def __str__(self):
        status = "正确" if self.is_correct else "错误"
        # 确保 exercise 对象存在，避免在 admin 或 shell 中显示时出错
        exercise_str = str(self.exercise) if self.exercise else "未知习题"
        # 确保 user 对象存在
        user_str = self.user.username if self.user else "未知用户"
        return f"{user_str} 尝试 {exercise_str} - {status} ({self.attempted_at.strftime('%Y-%m-%d %H:%M')})"

class UserMistakeCollection(models.Model):
    """用户错题集"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mistake_collections', verbose_name='用户')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='in_mistake_collections', verbose_name='习题')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    last_attempt_at = models.DateTimeField(null=True, blank=True, verbose_name='最后一次尝试时间')
    attempt_count = models.IntegerField(default=0, verbose_name='尝试次数')
    correct_count = models.IntegerField(default=0, verbose_name='正确次数')
    notes = models.TextField(blank=True, verbose_name='笔记')
    
    class Meta:
        verbose_name = '用户错题集'
        verbose_name_plural = verbose_name
        unique_together = ['user', 'exercise']
        ordering = ['-added_at']
        
    def __str__(self):
        return f"{self.user.username}的错题: {self.exercise}"
    
    @property
    def accuracy_rate(self):
        """计算正确率"""
        if self.attempt_count == 0:
            return 0
        return (self.correct_count / self.attempt_count) * 100
