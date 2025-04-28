from django.db import models

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
    
    class Meta:
        verbose_name = '习题'
        verbose_name_plural = verbose_name
        ordering = ['order', 'number']
        
    def __str__(self):
        return f"{self.section} - 第{self.number}题"
