import os
import re
from django.core.management.base import BaseCommand
from courses.models import Book, Chapter, Section, Knowledge, Exercise
import shutil

class Command(BaseCommand):
    help = '从MD文件导入数据到数据库'

    def add_arguments(self, parser):
        parser.add_argument('data_dir', type=str, help='包含MD文件的目录路径')
        parser.add_argument('images_dir', type=str, help='包含图片的目录路径')

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        images_dir = options['images_dir']

        # 创建书籍
        books = {
            'cn': Book.objects.create(title='计算机网络', description='计算机网络考研教材'),
            'co': Book.objects.create(title='计算机组成原理', description='计算机组成原理考研教材'),
            'ds': Book.objects.create(title='数据结构', description='数据结构考研教材'),
            'os': Book.objects.create(title='操作系统', description='操作系统考研教材'),
        }

        # 复制图片到media目录
        media_root = 'media/images/'
        os.makedirs(media_root, exist_ok=True)
        
        for book_code in books.keys():
            book_images_dir = os.path.join(images_dir, book_code)
            if os.path.exists(book_images_dir):
                for img in os.listdir(book_images_dir):
                    src = os.path.join(book_images_dir, img)
                    dst = os.path.join(media_root, img)
                    shutil.copy2(src, dst)

        # 遍历目录处理每本书
        for book_code, book in books.items():
            book_dir = os.path.join(data_dir, book_code)
            if not os.path.exists(book_dir):
                continue

            # 处理章节
            for chapter_dir in sorted(os.listdir(book_dir)):
                if not chapter_dir.startswith('chapter_'):
                    continue

                chapter_num = int(chapter_dir.split('_')[1])
                chapter = Chapter.objects.create(
                    book=book,
                    number=chapter_num,
                    title=f'第{chapter_num}章'
                )

                # 处理小节
                chapter_path = os.path.join(book_dir, chapter_dir)
                for md_file in sorted(os.listdir(chapter_path)):
                    if not md_file.endswith('.md'):
                        continue

                    # 解析小节号和标题
                    match = re.match(r'(\d+\.\d+)_(.+)\.md', md_file)
                    if not match:
                        continue

                    section_num, section_title = match.groups()
                    section = Section.objects.create(
                        chapter=chapter,
                        number=section_num,
                        title=section_title
                    )

                    # 读取MD文件内容
                    with open(os.path.join(chapter_path, md_file), 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 分离知识点和习题
                    parts = content.split('#### 本节习题精选')
                    if len(parts) > 1:
                        knowledge_content = parts[0]
                        exercise_content = parts[1]

                        # 处理知识点
                        knowledge = Knowledge.objects.create(
                            section=section,
                            title=section_title,
                            content=knowledge_content,
                            order=0
                        )

                        # 处理习题
                        exercises = exercise_content.split('#### ')
                        for exercise in exercises:
                            if not exercise.strip():
                                continue

                            # 处理单选题
                            if '单项选择题' in exercise:
                                questions = re.split(r'\d+\.', exercise)[1:]  # 分割题目
                                for i, question in enumerate(questions, 1):
                                    # 提取选项
                                    options_match = re.findall(r'[A-D]\.(.*?)(?=[A-D]\.|\n|$)', question, re.DOTALL)
                                    options = {
                                        chr(65+j): opt.strip() 
                                        for j, opt in enumerate(options_match)
                                    } if options_match else {}

                                    Exercise.objects.create(
                                        section=section,
                                        type='single',
                                        number=f'{i:02d}',
                                        content=question.split('A.')[0].strip(),
                                        options=options,
                                        answer='',  # 答案需要从答案部分提取
                                        explanation='',  # 解析需要从答案部分提取
                                        order=i
                                    )

                            # 处理综合题
                            elif '综合应用题' in exercise:
                                questions = re.split(r'\d+．', exercise)[1:]
                                for i, question in enumerate(questions, 1):
                                    Exercise.objects.create(
                                        section=section,
                                        type='comprehensive',
                                        number=f'{i:02d}',
                                        content=question.strip(),
                                        options=None,
                                        answer='',  # 答案需要从答案部分提取
                                        explanation='',  # 解析需要从答案部分提取
                                        order=i
                                    )

        self.stdout.write(self.style.SUCCESS('数据导入完成')) 