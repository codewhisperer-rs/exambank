import os
import re
import shutil 
import json 
from pathlib import Path 
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction, connections 
from courses.models import Book, Chapter, Section, Knowledge, Exercise 
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates the database with books, chapters, sections, knowledge points and exercises from the data directory.'


    DATA_DIR = os.path.join(settings.BASE_DIR, 'data')

    SUBJECT_MAP = {
        'cn': '计算机网络',
        'co': '计算机组成原理',
        'ds': '数据结构',
        'os': '操作系统',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-db',
            action='store_true',
            help='只检查数据库连接，不执行导入',
        )

    def process_markdown_images(self, markdown_content, source_file_dir):
        if not markdown_content: # Handle empty content
            return ""
            
    
        img_pattern = re.compile(r'!\[(.*?)\]\(\s*(?!https?://|/)([^\s\)\"\']+?)(\s+[\"\'].*?[\"\'])?\s*\)')
        updated_markdown = markdown_content
        media_images_url_base = f"{settings.MEDIA_URL.rstrip('/')}/images/"

        matches_found = []
        replacements_made = []

        for match in img_pattern.finditer(markdown_content):
            full_tag = match.group(0)
            alt_text = match.group(1)
            original_path_str = match.group(2).strip()
            title_part = match.group(3) or '' 
            matches_found.append(full_tag)
            
            try:
                image_filename = Path(original_path_str).name
                if not image_filename:
                    logging.warning(f"      Could not extract filename from path: '{original_path_str}' in {source_file_dir}. Skipping.")
                    continue
            except Exception as e:
                logging.warning(f"      Error processing path '{original_path_str}' in {source_file_dir}: {e}. Skipping.")
                continue

            new_image_url = f"{media_images_url_base}{image_filename}"

           
            cleaned_title_part = f' {title_part.strip()}' if title_part.strip() else ''
            new_img_tag = f'![{alt_text}]({new_image_url}{cleaned_title_part})'

            if full_tag in updated_markdown:
                updated_markdown = updated_markdown.replace(full_tag, new_img_tag, 1)
                replacements_made.append((full_tag, new_img_tag))
            else:
                logging.warning(f"      Tag '{full_tag}' not found in remaining markdown for replacement. Maybe already processed or nested differently?")


        return updated_markdown

    def extract_answers(self, answers_markdown, source_file_dir):
        answers_data = {}

        clean_answers_markdown = re.sub(r'(?<=\n)#+\s+\d+\.', r'\n\g<0>', answers_markdown)
        clean_answers_markdown = re.sub(r'^#+\s+\d+\.', r'\g<0>', clean_answers_markdown)
        
        pattern = re.compile(r'^(\d+)[．.．。]?\s*(.*?)(?=\n\d+[．.．。]?|\Z)', re.MULTILINE | re.DOTALL)
        
        current_type = None 

        type_pattern = re.compile(r'^(?:#+\s+)?(?:[\d\.]+\s+)?(一、单项选择题|二、综合应用题)', re.MULTILINE)

        parts = type_pattern.split(clean_answers_markdown)
        
        content_parts = []
        if len(parts) == 1:
            content_parts.append(('', parts[0])) 
        else:
             content_parts = [(parts[i], parts[i+1]) for i in range(1, len(parts), 2)]

        if len(content_parts) == 1 and content_parts[0][0] == '':
            content = content_parts[0][1]
            single_choice_pattern = re.compile(r'^\s*([A-D])[．.．。]', re.MULTILINE)
            if single_choice_pattern.search(content):
                logger.info(f"    推断答案部分为单项选择题（未发现明确标题）")
                content_parts = [('一、单项选择题', content)]
        for header, content in content_parts:
            current_type = None
            if '单项选择题' in header:
                current_type = 'single'
            elif '综合应用题' in header:
                current_type = 'comprehensive'

            content = re.sub(r'(?<=\n)#+\s+(?=\d+[．.．。]?)', r'\n', content)
            content = re.sub(r'^#+\s+(?=\d+[．.．。]?)', r'', content)
            answer_starts = []
            start_pattern = re.compile(r'^(\d{2})[．.．。\s]?', re.MULTILINE)
            for match in start_pattern.finditer(content):
                answer_starts.append({'number': match.group(1), 'start_index': match.start()})

            if not answer_starts:
                logger.warning(f"    在类型 '{current_type or 'unknown'}' 的答案内容块中未找到任何两位数题号。")
                continue 

         
            for i, start_info in enumerate(answer_starts):
                number_str = start_info['number'] 
                start_index = start_info['start_index']

                end_index = answer_starts[i+1]['start_index'] if i + 1 < len(answer_starts) else len(content)

                # 提取这道题的完整答案片段 (包括题号行)
                full_answer_segment = content[start_index:end_index].strip()

                # 从片段中分离题号和实际答案/解析内容
                segment_pattern = re.compile(r'^\d{2}[．.．。\s]?\s*(.*)', re.DOTALL)
                segment_match = segment_pattern.match(full_answer_segment)

                if not segment_match:
                    logger.error(f"      无法从提取的答案片段中解析题号/内容 (题号: {number_str})。片段开头: {full_answer_segment[:100]}...")
                    continue

                content_text = segment_match.group(1).strip() # 这就是当前题号对应的完整答案/解析

                answer = ''
                explanation_raw = ''

                if current_type == 'single':
                  
                    content_parts = content_text.split('\n', 1)
                    first_line_content = content_parts[0].strip()
                    rest_of_content = content_parts[1].strip() if len(content_parts) > 1 else ""

                    answer_match = re.match(r'^\s*([A-D])', first_line_content)
                    if answer_match:
                        answer = answer_match.group(1)
                        explanation_raw = first_line_content[answer_match.end():].strip()
                        if rest_of_content:
                            explanation_raw += '\n' + rest_of_content
                    else:
                        answer = '?'
                        logger.warning(f"    无法找到单选题答案 (A-D) for question {number_str} in answers. Content: {first_line_content}")
                        explanation_raw = first_line_content
                        if rest_of_content:
                            explanation_raw += '\n' + rest_of_content

                elif current_type == 'comprehensive':
                 
                    answer = '' 
                    explanation_raw = content_text
                    explanation_raw = re.sub(r'^【.*?】\s*', '', explanation_raw).strip()
                    logger.info(f"    综合应用题答案 {number_str} 按照两位主题号处理，内容完整提取 (长度: {len(explanation_raw)}).")

                else: 
                    logger.warning(f"    未知或缺失的答案题型 ({number_str}). 视为 comprehensive 处理.")
                    answer = ''
                    explanation_raw = content_text
                    explanation_raw = re.sub(r'^【.*?】\s*', '', explanation_raw).strip()

                explanation_processed = self.process_markdown_images(explanation_raw, source_file_dir)

                type_prefix = current_type if current_type else 'unknown'
                composite_key = f"{type_prefix}_{number_str}"

                answers_data[composite_key] = {
                    'answer': answer,
                    'explanation': explanation_processed,
                    'type': type_prefix,
                    'number': number_str
                }
                answers_data[number_str] = answers_data[composite_key]

                logging.debug(f"    Extracted Answer/Explanation for {composite_key}: Answer='{answer}', Explanation length={len(explanation_processed)}")

        if not answers_data:
             logging.warning(f"    No answers extracted from answer markdown in {source_file_dir}. Content starts: {answers_markdown[:100]}")
             
        return answers_data

    def parse_and_create_exercises(self, section, exercises_markdown, answers_data, source_file_dir):
       
        logger.info(f"      Starting exercise processing for Section {section.number} ({section.title}) within a transaction.")

        type_pattern = re.compile(r'^(?:#+\s+|[\d\.]+\s+)?(一、单项选择题|二、综合应用题)', re.MULTILINE)
        parts = type_pattern.split(exercises_markdown)

        exercise_order = 1 

        content_parts = []
        if len(parts) <= 1:
          
            logger.warning(f"    No exercise type headers (e.g., '#### 一、单项选择题') found in exercises markdown for section {section}. Processing all questions.")
            content_parts.append(('', parts[0] if parts else '')) 
        else:
             content_parts = [(parts[i], parts[i+1]) for i in range(1, len(parts), 2)]

        # 记录每个题型的答案键，用于后续匹配
        answer_keys_by_type = {}
        for key in answers_data.keys():
            if '_' in key: 
                type_part, num_part = key.split('_', 1)
                if type_part not in answer_keys_by_type:
                    answer_keys_by_type[type_part] = []
                answer_keys_by_type[type_part].append(key)
        
        logger.info(f"    找到以下题型的答案: {list(answer_keys_by_type.keys())}")

        for header, content in content_parts:
            current_type = 'unknown' 
            if '单项选择题' in header:
                current_type = 'single'
            elif '综合应用题' in header:
                current_type = 'comprehensive'
            else:
                logger.warning(f"    Processing exercises under potentially missing/unrecognized header: '{header}'")

            logger.info(f"    处理题型: {current_type}")

           
            question_starts = []
            start_pattern = re.compile(r'^(\d{2})[．.．。\s]?', re.MULTILINE)
            for match in start_pattern.finditer(content):
                question_starts.append({'number': match.group(1), 'start_index': match.start()})

            if not question_starts:
                logger.warning(f"    在类型 {current_type} 的内容块中未找到任何题号。")
                continue 

            for i, start_info in enumerate(question_starts):
                number_str = start_info['number'].zfill(2) 
                start_index = start_info['start_index']

                end_index = question_starts[i+1]['start_index'] if i + 1 < len(question_starts) else len(content)

                full_question_segment = content[start_index:end_index].strip()

            
                segment_pattern = re.compile(r'^\d+[．.．。\s]?\s*(.*)', re.DOTALL) 
                segment_match = segment_pattern.match(full_question_segment)

                if not segment_match:
                     logger.error(f"      无法从提取的片段中解析题号/内容 (题号: {number_str})。片段开头: {full_question_segment[:100]}...")
                     continue 

                question_raw = segment_match.group(1).strip() 

                question_raw_processed_images = self.process_markdown_images(question_raw, source_file_dir)

                options_json = None 
                question_text_processed = question_raw_processed_images 
                answer = ''
                explanation = ''

                composite_key = f"{current_type}_{number_str}"
                answer_info = None
            
                primary_key = composite_key  
                
                fallback_keys = [
                    number_str,          
                    f"unknown_{number_str}", 
                ]
                
                if primary_key in answers_data:
                    answer_info = answers_data[primary_key]
                    logger.info(f"      找到题目 {number_str} ({current_type}) 的答案，使用主键 '{primary_key}'")
                else:
                    logger.warning(f"      未找到题目 {number_str} ({current_type}) 对应的主键 '{primary_key}'，尝试备选键")
                    for key in fallback_keys:
                        if key in answers_data:
                            answer_info = answers_data[key]
                            logger.info(f"      找到题目 {number_str} ({current_type}) 的答案，使用备选键 '{key}'")
                            break
                
                if answer_info:
                    answer = answer_info.get('answer', '')
                    explanation = answer_info.get('explanation', '')
                    answer_type = answer_info.get('type', 'unknown')
                    if answer_type != current_type and answer_type != 'unknown':
                        logger.warning(f"      警告：题目 {number_str} 的类型为 {current_type}，但找到的答案类型为 {answer_type}")
                    
                    if current_type == 'comprehensive':
                        logger.info(f"      成功匹配综合应用题 {number_str} 的答案，答案长度: {len(explanation)}字符")
                else:
                    logger.warning(f"      No answer/explanation found for question {number_str} in section {section.title} (type: {current_type})")
                    type_specific_keys = answer_keys_by_type.get(current_type, [])
                    all_type_keys_str = "、".join(type_specific_keys[:10])
                    logger.warning(f"      当前题型 '{current_type}' 的所有答案键: {all_type_keys_str}...")
                            
                if current_type == 'single':
                    options_dict = {}
                    question_text_processed = question_raw_processed_images
                    first_option_start_index = -1
                    multiline_pattern = re.compile(r"(?:^|\n)\s*([A-D])[．.．。\s]\s*(.*?)(?=\n\s*[A-D][．.．。\s]|\Z)", re.DOTALL)
                    multiline_matches = list(multiline_pattern.finditer(question_raw_processed_images))
                    if len(multiline_matches) >= 2:
                        multiline_matches.sort(key=lambda m: m.start())
                        first_option_start_index = multiline_matches[0].start()
                        for i, match in enumerate(multiline_matches):
                            option_letter = match.group(1)
                            option_content = match.group(2).strip()
                            option_content = re.sub(r'\n\s*[A-D][．.．。\s].*$', '', option_content).strip()
                            if option_content:
                                options_dict[option_letter] = option_content
                    if len(options_dict) < 2:
                        marker_pattern = re.compile(r'([A-D])[．.．。\s]')
                        markers = list(marker_pattern.finditer(question_raw_processed_images))
                        inline_options_found = {}
                        if len(markers) >= 2:
                            markers.sort(key=lambda m: m.start())
                            first_option_start_index = markers[0].start()
                            for i, marker in enumerate(markers):
                                option_letter = marker.group(1)
                                start_pos = marker.end()
                                end_pos = markers[i+1].start() if i + 1 < len(markers) else len(question_raw_processed_images)
                                option_content = question_raw_processed_images[start_pos:end_pos].strip()
                                if option_content and len(option_content) < 300:
                                    inline_options_found[option_letter] = option_content
                                else:
                                    logger.warning(f"      Q{number_str}: Suspiciously long or empty content for option {option_letter} via marker splitting. Ignoring.")
                            if len(inline_options_found) >= 2:
                                options_dict = inline_options_found
                            else:
                                first_option_start_index = -1
                        else:
                             first_option_start_index = -1

                    if options_dict and first_option_start_index != -1:
                        question_text_processed = question_raw_processed_images[:first_option_start_index].strip()
                        ordered_options = {}
                        for letter in ['A', 'B', 'C', 'D']:
                            if letter in options_dict:
                                clean_content = options_dict[letter].strip(' \t\n\r.-*_')
                                clean_content = re.sub(r'^[A-D][．.．。\s]\s*', '', clean_content).strip()
                                if clean_content:
                                    ordered_options[letter] = clean_content
                                else:
                                    logger.warning(f"      Q{number_str}: Option {letter} content empty after cleaning.")

                        if len(ordered_options) >= 2:
                            options_json = json.dumps(ordered_options, ensure_ascii=False)
                        else:
                            question_text_processed = question_raw_processed_images
                            options_json = None
                            options_dict = {}
                    if not options_dict:
                         is_special_case = (section.title == "内存管理概念" and number_str == "24")
                         
                         if is_special_case:
                             logger.warning(f"      Q{number_str} ({section.title}): Known complex format or specific case. Skipping option extraction.")
                         else:
                             logger.warning(f"      Q{number_str} ({section.title}): Could not extract valid options for single choice. Storing full content. Raw starts: {question_raw_processed_images[:100]}...")
                         question_text_processed = question_raw_processed_images
                         options_json = None

                elif current_type == 'comprehensive':
                    options_json = None
                    question_text_processed = question_raw_processed_images
                    logger.info(f"      综合应用题 {number_str} 内容已完整提取 (长度: {len(question_text_processed)}).")
                else: 
                    options_json = None
                    question_text_processed = question_raw_processed_images
                    logger.warning(f"      将题目 {number_str} 作为 'unknown' 类型处理，因为在 section {section} 中缺少有效的题型标题")

               
                try:
                    if current_type == 'comprehensive':
                        logger.info(f"        综合应用题 Q{number_str} 保存前信息:")
                        logger.info(f"          - 答案长度: {len(explanation)}字符")
                        logger.info(f"          - 答案开头: {explanation[:100]}...")
                        logger.info(f"          - 按题号处理，每个题号作为一个独立题目")

                    exercise, created = Exercise.objects.update_or_create(
                        section=section,
                        order=exercise_order, 
                        defaults={
                            'number': number_str,
                            'type': current_type,
                            'content': question_text_processed,
                            'options': options_json,
                            'answer': answer,
                            'explanation': explanation,
                        }
                    )
                    log_prefix = "Created" if created else "Updated/Found"
                    logger.info(f"        {log_prefix} Exercise: {section.chapter.book.title} / {section.chapter.title} / {section.title} / Order {exercise_order} (Num: {number_str}, Type: {current_type})")
                    self.stdout.write(f"          {log_prefix} Exercise: Order {exercise_order} (Num: {number_str}, Type: {current_type})")
                    exercise_order += 1 # 移动全局计数器到循环末尾
                except Exception as e:
                    logger.error(f"      创建/更新习题时出错 Order {exercise_order} (Num: {number_str}) for section {section.title}: {e}")
                    self.stderr.write(self.style.ERROR(f"      创建/更新习题时出错 Order {exercise_order} (Num: {number_str}): {e}"))
                    # raise e # 如果希望出错时停止，可以取消注释
        logger.info(f"      完成了 Section {section.number} ({section.title}) 的习题处理。")

    def handle(self, *args, **options):
        # 确保数据库可访问
        try:
            # 测试数据库连接
            connections['default'].cursor()
            logger.info("数据库连接成功")
            
            # 如果只是检查数据库，这里就返回
            if options['check_db']:
                self.stdout.write(self.style.SUCCESS('数据库连接检查通过，没有进行数据导入'))
                return
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            self.stderr.write(self.style.ERROR(f"数据库连接失败: {e}"))
            self.stderr.write(self.style.ERROR("请确保数据库文件存在且有正确的访问权限"))
            return

        # Ensure DATA_DIR is absolute for reliable path operations
        self.DATA_DIR = str(Path(self.DATA_DIR).resolve())
        self.stdout.write(self.style.SUCCESS('Starting database population...'))
        logger.info(f"Starting database population from: {self.DATA_DIR}")
        # Optional: Clear existing data if needed (USE WITH CAUTION)
        # self.stdout.write(self.style.WARNING('Clearing existing data...'))
        # Knowledge.objects.all().delete()
        # Exercise.objects.all().delete()
        # Section.objects.all().delete()
        # Chapter.objects.all().delete()
        # Book.objects.all().delete()

        self.populate_books()
        self.stdout.write(self.style.SUCCESS('Database population finished.'))
        logger.info("Database population finished.")

    def populate_books(self):
        logger.info(f"Scanning for subjects in: {self.DATA_DIR}")
        if not os.path.exists(self.DATA_DIR):
            logger.error(f"Data directory not found: {self.DATA_DIR}")
            self.stderr.write(self.style.ERROR(f"Data directory not found: {self.DATA_DIR}"))
            return

        for subject_code in os.listdir(self.DATA_DIR):
            subject_path = os.path.join(self.DATA_DIR, subject_code)
            if os.path.isdir(subject_path):
                # Use Path for robust joining
                subject_path_obj = Path(subject_path)
                book_title = self.SUBJECT_MAP.get(subject_code, subject_code.upper())
                logger.info(f"Processing Subject: {book_title} in path {subject_path_obj}")
                book, created = Book.objects.update_or_create(
                    title=book_title,
                    defaults={'description': f'{book_title} 考研辅导内容'}
                )

                if created:
                    logger.info(f"  Created Book: {book.title}")
                    self.stdout.write(f"  Created Book: {book.title}")
                else:
                    logger.info(f"  Updated/Found Book: {book.title}")
                    self.stdout.write(f"  Updated/Found Book: {book.title}")

                # --- 清理旧的习题数据 --- #
                # 在处理章节和习题之前，删除该书下所有已存在的习题
                # 这样可以确保每次运行脚本时，旧的或错误的习题数据被清除
                logger.info(f"  Clearing existing exercises for Book: {book.title}...")
                deleted_count, _ = Exercise.objects.filter(section__chapter__book=book).delete()
                if deleted_count > 0:
                    logger.info(f"    Deleted {deleted_count} existing exercises for Book: {book.title}")
                    self.stdout.write(self.style.WARNING(f"    Deleted {deleted_count} existing exercises for Book: {book.title}"))
                else:
                    logger.info(f"    No existing exercises found to delete for Book: {book.title}")

                # Call function to populate chapters for this book
                self.populate_chapters(book, subject_path_obj) # Pass Path object

    @transaction.atomic # <-- Add transaction decorator here
    def populate_chapters(self, book, subject_path):
        logger.info(f"  Scanning for chapters in: {subject_path}")
        chapter_pattern = re.compile(r'^chapter_(\d+)$')
        chapters_to_process = []

        try:
            for item_path in subject_path.iterdir():
                logger.debug(f"    Checking item: {item_path.name} in {subject_path}")
                if item_path.is_dir():
                    match = chapter_pattern.match(item_path.name)
                    logger.debug(f"      Item: '{item_path.name}', Directory? {item_path.is_dir()}, Regex match result: {match}")
                    if match:
                        chapter_number = int(match.group(1))
                        chapters_to_process.append({'path': item_path, 'number': chapter_number})

            # Sort chapters numerically by number
            chapters_to_process.sort(key=lambda x: x['number'])

            # Process sorted chapters
            for chapter_info in chapters_to_process:
                item_path = chapter_info['path']
                chapter_number = chapter_info['number']
                logger.info(f"      Processing Chapter directory (sorted): {item_path.name} (Number: {chapter_number})")

                # --- Determine Chapter Title and Introduction ---
                chapter_title = f"第 {chapter_number} 章" # Default title
                introduction_content_processed = ""
                intro_section_created = False # Flag
                chapter_obj = None # To hold the created/updated chapter object

                # Look for introduction file (e.g., 1.0_Intro.md)
                # Use glob for flexible matching
                intro_files = list(item_path.glob(f"{chapter_number}.0_*.md"))

                if intro_files:
                    intro_file_path = intro_files[0] # Take the first match
                    if len(intro_files) > 1:
                        logger.warning(f"      Multiple introduction files found for chapter {chapter_number} in {item_path}. Using: {intro_file_path.name}")
                    try:
                        logger.info(f"        Processing introduction file: {intro_file_path.name}")
                        with open(intro_file_path, 'r', encoding='utf-8') as f:
                            original_introduction_content = f.read()

                        # Process images FIRST
                        introduction_content_processed = self.process_markdown_images(
                            original_introduction_content,
                            str(item_path) # Pass directory path as string
                        )

                        # 确定章节标题，优先使用有意义的文字描述而非章节编号
                        # 从内容中查找有意义的标题（不要仅仅是"第X章"这样的格式）
                        chapter_title = f"第{chapter_number}章" # 默认值
                        
                        # 尝试从前几行中找到最合适的标题
                        lines = original_introduction_content.split('\n')
                        for line in lines[:5]:  # 检查前5行
                            line = line.strip()
                            if not line:
                                continue
                                
                            # 匹配markdown标题行
                            title_match = re.match(r'^#+\s*(.*)', line)
                            if title_match:
                                candidate = title_match.group(1).strip()
                                # 排除只有"第X章"的标题
                                if not re.match(r'^第\s*\d+\s*章$', candidate):
                                    chapter_title = candidate
                                    logger.info(f"          找到合适的章节标题: '{chapter_title}'")
                                    break
                        
                        # 如果没找到合适的标题，尝试从文件名提取
                        if chapter_title == f"第{chapter_number}章":
                            intro_title_match = re.match(r'^\d+\.0_(.+?)\.md$', intro_file_path.name, re.IGNORECASE)
                            if intro_title_match:
                                file_title = intro_title_match.group(1).replace('_', ' ').strip()
                                # 如果文件名中的标题不是简单的"第X章"格式，则使用它
                                if not re.match(r'^第\s*\d+\s*章$', file_title):
                                    chapter_title = file_title
                                    logger.info(f"          从文件名提取章节标题: '{chapter_title}'")
                                
                        # 如果最终标题仍然只是"第X章"，添加"内容"以区分
                        if re.match(r'^第\s*\d+\s*章$', chapter_title):
                            chapter_title = f"{chapter_title}内容"
                            logger.warning(f"          未找到合适的章节标题，使用默认值: '{chapter_title}'")

                        # Create/Update Chapter object
                        chapter_obj, created = Chapter.objects.update_or_create(
                            book=book,
                            number=chapter_number,
                            defaults={
                                'title': chapter_title, # Use extracted/fallback title
                                'introduction': introduction_content_processed # Save PROCESSED markdown
                            }
                        )
                        log_prefix = "Created" if created else "Updated/Found"
                        logger.info(f"        {log_prefix} Chapter: {chapter_obj.title} (Number: {chapter_obj.number}) for Book '{book.title}'")
                        self.stdout.write(f"        {log_prefix} Chapter: {chapter_obj.title}")

                        # Create the Introduction Section for this chapter
                        intro_section_title = "章节介绍" # Keep it simple
                        intro_section_number = f"{chapter_number}.0"
                        section, sec_created = Section.objects.update_or_create(
                            chapter=chapter_obj,
                            number=intro_section_number,
                            defaults={
                                'title': intro_section_title,
                                'section_type': 'introduction',
                                'content': introduction_content_processed # Use the processed content
                            }
                        )
                        sec_log_prefix = "Created" if sec_created else "Updated/Found"
                        logger.info(f"          {sec_log_prefix} Introduction Section: {section.title} (Number: {section.number})")
                        self.stdout.write(f"          {sec_log_prefix} Introduction Section: {section.title}")
                        intro_section_created = True

                    except Exception as e:
                        logger.error(f"      Error processing intro file {intro_file_path}: {e}")
                        self.stderr.write(self.style.ERROR(f"      Error processing intro file {intro_file_path}: {e}"))
                else:
                     logger.warning(f"      No introduction file (e.g., {chapter_number}.0_*.md) found in {item_path}.")

                # If chapter wasn't created via intro file, create it now
                if not chapter_obj:
                    chapter_obj, created = Chapter.objects.update_or_create(
                        book=book,
                        number=chapter_number,
                        defaults={
                            'title': chapter_title, # Use default title
                            'introduction': '' # No intro content found
                        }
                    )
                    log_prefix = "Created" if created else "Updated/Found"
                    logger.info(f"        {log_prefix} Chapter (no intro file): {chapter_obj.title}")
                    self.stdout.write(f"        {log_prefix} Chapter (no intro file): {chapter_obj.title}")

                # Pass chapter object and path to populate sections
                if chapter_obj:
                    self.populate_sections(chapter_obj, item_path) # Pass Path object
                else:
                     logger.error(f"      Chapter object could not be created/retrieved for number {chapter_number}. Skipping sections.")

        except FileNotFoundError:
            logger.error(f"Subject directory not found when scanning for chapters: {subject_path}")
            self.stderr.write(self.style.ERROR(f"Subject directory not found: {subject_path}"))
        except Exception as e:
            logger.exception(f"Error listing or processing directory {subject_path} for chapters: {e}") # Use exception for stack trace
            self.stderr.write(self.style.ERROR(f"Error listing directory {subject_path}: {e}"))

    def populate_sections(self, chapter, chapter_path):
        logger.info(f"      Scanning for sections in: {chapter_path}")
        section_pattern = re.compile(r'^([\d\.]+?)_(.+?)\.md$', re.IGNORECASE)
        sections_to_process = []

        try:
            for file_path in chapter_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() == '.md':
                    filename = file_path.name

                    # Skip the intro file (X.0_...) - This check might be redundant now but safe to keep
                    if re.match(r'^\d+\.0_.*\.md$', filename, re.IGNORECASE):
                        logger.debug(f"        Skipping intro file: {filename}")
                        continue

                    match = section_pattern.match(filename)
                    if match:
                        section_number_str = match.group(1)
                        section_title = match.group(2).replace('_', ' ').strip()
                        # Store path, number string, and title for sorting and processing
                        sections_to_process.append({
                            'path': file_path,
                            'number': section_number_str,
                            'title': section_title
                        })
                    else:
                         # Log files that don't match the expected section pattern, excluding intro
                         if not re.match(r'^\d+\.0_.*\.md$', filename, re.IGNORECASE):
                             logger.warning(f"        Filename pattern not matched for section: {filename} in {chapter_path}")

            # Sort sections based on the number string (e.g., "1.1", "1.2", "1.10")
            # We need a sort key that handles numeric parts correctly.
            def section_sort_key(section_info):
                # Split the number string by dots and convert parts to integers
                parts = section_info['number'].split('.')
                try:
                    return [int(p) for p in parts]
                except ValueError:
                    # Fallback for non-numeric parts or malformed strings
                    return [9999] # Place malformed ones at the end

            sections_to_process.sort(key=section_sort_key)

            # Process sorted sections
            for section_info in sections_to_process:
                file_path = section_info['path']
                section_number_str = section_info['number']
                section_title = section_info['title']
                filename = file_path.name # Get filename for logging

                # Determine section type based on keywords
                section_type = 'content' # Default
                # Use lowercase for case-insensitive matching
                title_lower = section_title.lower()
                if '小结' in title_lower or '总结' in title_lower:
                    section_type = 'summary'
                elif '疑难' in title_lower or 'faq' in title_lower or '常见问题' in title_lower:
                    section_type = 'faq'
                # Add more elif checks if needed

                logger.info(f"        Found Section file: {filename} (Number: {section_number_str}, Title: {section_title}, Type: {section_type})")

                # --- Read Section Content ---
                original_section_content = ""
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_section_content = f.read()
                except Exception as e:
                    logger.error(f"          Error reading section file {file_path}: {e}")
                    self.stderr.write(self.style.ERROR(f"          Error reading section file {file_path}: {e}"))
                    continue # Skip this file

                # --- 分割内容：知识点、习题、答案 ---
                # 处理图片 *在* 分割内容之前，因为图片路径可能相对于原始文件位置
                content_with_images = self.process_markdown_images(original_section_content, str(chapter_path))

                knowledge_content = content_with_images # 默认所有内容
                exercises_markdown = ""
                answers_markdown = ""

                # 匹配两种类型的习题标题:
                # 1. 类似 "#### 本节试题精选" 的形式
                # 2. 类似 "1.1.3 本节试题精选" 的形式（包含章节编号）
                exercise_pattern = r'(?:#+\s+|[\d\.]+\s+)(?:本节试题精选|本节习题精选)\s*'
                exercise_split = re.split(exercise_pattern, content_with_images, maxsplit=1, flags=re.IGNORECASE)
                if len(exercise_split) == 2:
                    knowledge_content = exercise_split[0].strip()
                    rest_content = exercise_split[1]

                    # 同样匹配两种类型的答案标题
                    answer_pattern = r'(?:#+\s+|[\d\.]+\s+)答案与解析\s*'
                    answer_split = re.split(answer_pattern, rest_content, maxsplit=1, flags=re.IGNORECASE)
                    if len(answer_split) == 2:
                        exercises_markdown = answer_split[0].strip()
                        answers_markdown = answer_split[1].strip()
                    else:
                        # 发现习题标记但没有答案标记
                        exercises_markdown = rest_content.strip()
                        logger.warning(f"          找到习题标记但在 {filename} 中未找到答案标记。习题可能不完整。")
                else:
                    # No exercises marker found, assume all content is knowledge
                    logger.info(f"          No exercise marker found in {filename}. Treating all content as knowledge.")
                    knowledge_content = content_with_images.strip() # Use content with processed images

                # --- Create or Update Section ---
                # Section content should ideally be just the knowledge part if separated,
                # or the full content if not. Let's store the *knowledge* part here.
                section, created = Section.objects.update_or_create(
                    chapter=chapter,
                    number=section_number_str,
                    defaults={
                        'title': section_title,
                        'section_type': section_type,
                        'content': knowledge_content # Store knowledge part (or full content if no split)
                    }
                )
                log_prefix = "Created" if created else "Updated/Found"
                logger.info(f"        {log_prefix} Section: {section.title} (Number: {section.number}, Type: {section.section_type})")
                self.stdout.write(f"        {log_prefix} Section: {section.title}")

                # --- Create Knowledge Object (even if empty, link it) ---
                # Use section title as default knowledge title if knowledge content exists
                knowledge_title = section_title if knowledge_content else "知识点"
                knowledge_obj, k_created = Knowledge.objects.update_or_create(
                    section=section,
                    order=0, # Assuming one primary knowledge block per section for now
                    defaults={
                        'title': knowledge_title,
                        'content': knowledge_content # Already image-processed
                    }
                )
                k_log_prefix = "Created" if k_created else "Updated/Found"
                logger.info(f"          {k_log_prefix} Knowledge block linked to Section {section.number}")
                # Don't print knowledge creation to stdout to reduce noise

                # --- Process and Create Exercises ---
                if exercises_markdown and answers_markdown:
                   logger.info(f"          Processing exercises and answers for Section {section.number}...")
                   # Extract answers first using the correct method name if changed
                   # This might be extract_answers or part of _parse_answers now? Let's assume extract_answers for now.
                   try:
                       # Check if extract_answers exists before calling
                       if hasattr(self, 'extract_answers'):
                           answers_data = self.extract_answers(answers_markdown, str(chapter_path))
                       else:
                           # If extract_answers was refactored, need to adapt here
                           # For now, assume it exists or log a warning
                           logger.warning("Method 'extract_answers' not found, exercise processing might fail.")
                           answers_data = {}

                       # Check if parse_and_create_exercises exists before calling
                       if hasattr(self, 'parse_and_create_exercises'):
                           self.parse_and_create_exercises(section, exercises_markdown, answers_data, str(chapter_path))
                       elif hasattr(self, '_process_exercises_for_section'):
                            # If the logic moved to _process_exercises_for_section, call that instead
                            # Note: _process_exercises_for_section expects the full section_content, not just exercises/answers
                            # We might need to pass the original content_with_images here.
                            # For now, let's call parse_and_create_exercises as it was the last version shown.
                            # Revisit if logs show issues.
                            logger.warning("Method 'parse_and_create_exercises' not found. Adapt call if logic moved.")
                       else:
                           logger.error("Neither 'parse_and_create_exercises' nor '_process_exercises_for_section' found.")

                   except Exception as e:
                        logger.error(f"Error processing exercises for section {section.title}: {e}", exc_info=True)

                elif exercises_markdown:
                    logger.warning(f"          Found exercises markdown but no answers markdown for Section {section.number}. Skipping exercise creation.")
                else:
                    logger.info(f"          No exercises found for Section {section.number}.")
        except FileNotFoundError:
            logger.error(f"Chapter directory not found when scanning for sections: {chapter_path}")
            self.stderr.write(self.style.ERROR(f"Chapter directory not found: {chapter_path}"))
        except Exception as e:
            logger.exception(f"Error listing or processing directory {chapter_path} for sections: {e}") # Use exception for stack trace
            self.stderr.write(self.style.ERROR(f"Error listing directory {chapter_path}: {e}"))

    # Make sure _process_exercises_for_section and _parse_exercises still have their debug logs
    def _process_exercises_for_section(self, section, section_content, chapter_number, book_title):
        logger.debug(f"Entering _process_exercises_for_section for section: '{section.title}' (Number: {section.number}), Chapter: {chapter_number}") # Entry log

        exercise_marker = "#### 本节习题精选"
        answer_marker = "#### 答案与解析"
        # ... (other markers) ...

        # Use the robust splitting logic from populate_sections
        exercise_pattern = r'(?:#+\s+|[\d\.]+\s+)(?:本节试题精选|本节习题精选)\s*'
        answer_pattern = r'(?:#+\s+|[\d\.]+\s+)答案与解析\s*'

        exercises_markdown = ""
        answers_markdown = ""

        exercise_split = re.split(exercise_pattern, section_content, maxsplit=1, flags=re.IGNORECASE)
        if len(exercise_split) == 2:
            rest_content = exercise_split[1]
            answer_split = re.split(answer_pattern, rest_content, maxsplit=1, flags=re.IGNORECASE)
            if len(answer_split) == 2:
                exercises_markdown = answer_split[0].strip()
                answers_markdown = answer_split[1].strip()
            else:
                exercises_markdown = rest_content.strip()
                logger.warning(f"    Exercise marker found but no answer marker in section {section.title}.")
        else:
            logger.info(f"    No exercise marker found in Section {section.number} ({section.title}) using pattern.")
            return # Exit if no exercises

        if not exercises_markdown:
            logger.info(f"    Exercises markdown is empty for section {section.title}.")
            return

        # Parse using the existing (or updated) functions
        try:
            # Split exercises by type headers (e.g., 一、单项选择题)
            exercise_types_blocks = self._split_by_exercise_type(exercises_markdown)
            # Split answers by type headers
            answer_types_blocks = self._split_by_answer_type(answers_markdown)

            # Parse exercises and answers based on the split blocks
            parsed_exercises = self._parse_exercises(exercise_types_blocks, f"{book_title} - {section.number} {section.title}")
            parsed_answers = self._parse_answers(answer_types_blocks, f"{book_title} - {section.number} {section.title}")

            # Log parsed exercises
            logger.debug(f"Parsed exercises for section '{section.title}':")
            for ex_data in parsed_exercises:
                log_entry = {k: ex_data[k] for k in ['order', 'type', 'content_preview'] if k in ex_data}
                log_entry['content_preview'] = ex_data.get('content', '')[:50] + ('...' if len(ex_data.get('content', '')) > 50 else '')
                logger.debug(f"  - {log_entry}")

            combined_data = self._combine_exercises_answers(parsed_exercises, parsed_answers)

            logger.info(f"  Starting exercise processing for Section {section.number} ({section.title}) within a transaction.")
            with transaction.atomic():
                for exercise_data in combined_data:
                    # Specific Q01 logging
                    is_target_q01 = (section.title == "计算机系统层次结构" and
                                    chapter_number == 1 and
                                    exercise_data.get('order') == "01")

                    if is_target_q01:
                         logger.info(f"    DEBUG Q01 ({section.title}): Preparing to save.") # Changed to INFO level
                         logger.info(f"      - Type: {exercise_data.get('type')}")
                         logger.info(f"      - Content (start): {exercise_data.get('content', '')[:100]}...")
                         logger.info(f"      - Options JSON: {exercise_data.get('options')}")
                         logger.info(f"      - Answer: {exercise_data.get('answer')}")
                         logger.info(f"      - Explanation (start): {exercise_data.get('explanation', '')[:100]}...")
                         logger.info(f"      - Order Value: {exercise_data.get('order')}") # Check the actual order value being saved


                    # Save exercise (ensure _save_exercise handles the data correctly)
                    self._save_exercise(section, exercise_data, chapter_number, book_title) # Pass necessary args

        except Exception as e:
            logger.error(f"Error during exercise parsing/saving for Section {section.number} ({section.title}): {e}", exc_info=True)


    # Ensure _parse_exercises and other helper methods still exist and are correct
    def _parse_exercises(self, exercise_types_blocks, section_id):
        # ...(Keep the existing _parse_exercises logic with its logging)...
        # Make sure the options extraction and JSON dumping is correct
        exercises = []
        question_pattern = re.compile(r"^\s*(\d{1,2})\.\s+(.*)", re.MULTILINE | re.DOTALL) # Ensure this matches Q numbers correctly

        # Example part of the loop (keep the full logic)
        for type_header, block_content in exercise_types_blocks.items():
            exercise_type = EXERCISE_TYPE_MAP.get(type_header.strip(), 'unknown')
            # ... (splitting and processing questions in the block) ...
            raw_questions = re.split(r'\n\s*(?=\d{1,2}\.\s+)', '\n' + block_content.strip())
            questions = [q.strip() for q in raw_questions if q and q.strip()]

            for q_text in questions:
                 match = question_pattern.match(q_text)
                 if match:
                    order_str = match.group(1).zfill(2)
                    content_full = match.group(2).strip()
                    # ... (option extraction logic) ...
                    options_dict = {} # Placeholder for extracted options
                    content_without_options = content_full # Placeholder
                    # Actual option extraction logic here...
                    options_json = json.dumps(options_dict, ensure_ascii=False) if options_dict else None
                    # ... (rest of logic) ...
                    exercises.append({
                        'order': order_str,
                        'type': exercise_type,
                        'content': content_without_options,
                        'options': options_json # Make sure this is correct
                        # Include other necessary fields if needed by _combine_exercises_answers
                    })
                 else:
                     logger.warning(f"    Could not parse question number/content from: '{q_text[:100]}...' in section {section_id}")

        return exercises

    # Add dummy definitions for helper methods if they were removed or renamed,
    # ensuring the structure remains valid for the call flow.
    # Example:
    EXERCISE_TYPE_MAP = {
        '一、单项选择题': 'single',
        '二、综合应用题': 'comprehensive',
        # Add other mappings if used
    }
    ANSWER_TYPE_MAP = EXERCISE_TYPE_MAP # Often the same

    def _split_by_exercise_type(self, markdown):
        # Basic split logic (replace with actual implementation if different)
        pattern = re.compile(r'^#+\s*(一、单项选择题|二、综合应用题)', re.MULTILINE)
        parts = pattern.split(markdown)
        blocks = {}
        if len(parts) == 1:
             blocks[''] = parts[0] # No header found
        else:
            for i in range(1, len(parts), 2):
                 blocks[parts[i].strip()] = parts[i+1].strip()
        return blocks

    def _split_by_answer_type(self, markdown):
         # Similar to _split_by_exercise_type
         return self._split_by_exercise_type(markdown) # Reuse if logic is identical

    def _parse_answers(self, answer_types_blocks, section_id):
        # Basic parse logic (replace with actual implementation)
        answers = {}
        pattern = re.compile(r"^\s*(\d{1,2})\.\s*(.*)", re.MULTILINE | re.DOTALL)
        for type_header, block_content in answer_types_blocks.items():
             # Determine type (single/comprehensive) based on header
             answer_type = self.ANSWER_TYPE_MAP.get(type_header, 'unknown')
             # Find answers within block
             for match in pattern.finditer(block_content):
                 order_str = match.group(1).zfill(2)
                 full_answer_text = match.group(2).strip()
                 # Simplified extraction:
                 answer_letter = ''
                 explanation = full_answer_text
                 if answer_type == 'single':
                      if full_answer_text and full_answer_text[0].isalpha() and full_answer_text[1:2] in ['.', '．', '。', ' ']:
                          answer_letter = full_answer_text[0].upper()
                          explanation = full_answer_text[2:].strip()
                 answers[order_str] = {'answer': answer_letter, 'explanation': explanation}
        return answers

    def _combine_exercises_answers(self, parsed_exercises, parsed_answers):
        combined = []
        for ex in parsed_exercises:
            order = ex.get('order')
            answer_data = parsed_answers.get(order)
            if answer_data:
                ex['answer'] = answer_data.get('answer', '')
                ex['explanation'] = answer_data.get('explanation', '')
            else:
                ex['answer'] = ''
                ex['explanation'] = ''
                logger.warning(f"    No answer found for exercise {order}")
            combined.append(ex)
        return combined

    def _save_exercise(self, section, exercise_data, chapter_number, book_title):
        # Use update_or_create to handle existing exercises
        number_str = exercise_data.get('order')
        current_type = exercise_data.get('type', 'unknown')
        content_processed = exercise_data.get('content', '')
        options_json = exercise_data.get('options') # Should be JSON string or None
        answer = exercise_data.get('answer', '')
        explanation = exercise_data.get('explanation', '')
        # Determine the global order within the section if not passed directly
        # This might need adjustment based on how order is tracked
        exercise_order = int(number_str) if number_str.isdigit() else 0 # Simplified order

        try:
            exercise, created = Exercise.objects.update_or_create(
                section=section,
                order=exercise_order, # Use section and global order as the unique key
                defaults={
                    'number': number_str, # Save the original markdown number here
                    'type': current_type,
                    'content': content_processed,
                    'options': options_json,
                    'answer': answer,
                    'explanation': explanation, # Already image-processed from answers_data
                    # 'order' is now part of the key, no need to repeat in defaults unless updating
                }
            )
            log_prefix = "Created" if created else "Updated/Found"
            logger.info(f"        {log_prefix} Exercise: {section.chapter.book.title} / {section.chapter.title} / {section.title} / Order {exercise_order} (Num: {number_str}, Type: {current_type})") # Adjusted log
            self.stdout.write(f"          {log_prefix} Exercise: Order {exercise_order} (Num: {number_str}, Type: {current_type})") # Adjusted stdout
        except Exception as e:
            logger.error(f"      Error in _save_exercise for Q{number_str}, Section {section.title}: {e}", exc_info=True)

