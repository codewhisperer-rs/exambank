import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Exercise, ExerciseAttempt, UserMistakeCollection, AIGeneratedExercise, AIExerciseAttempt
import logging

logger = logging.getLogger(__name__)

class ExerciseConsumer(AsyncWebsocketConsumer):
    """
    处理习题相关WebSocket连接的异步消费者
    """
    async def connect(self):
        """
        建立WebSocket连接
        """
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # 从URL获取习题ID
        self.exercise_id = self.scope['url_route']['kwargs'].get('exercise_id')
        self.room_group_name = f'exercise_{self.exercise_id}'
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """
        关闭WebSocket连接
        """
        if hasattr(self, 'room_group_name'):
            # 离开房间组
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        接收WebSocket消息
        """
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'submit_answer':
                exercise_id = text_data_json.get('exercise_id')
                user_answer = text_data_json.get('user_answer')
                
                # 处理答案提交
                result = await self.submit_exercise_attempt(exercise_id, user_answer)
                
                # 发送响应
                await self.send(text_data=json.dumps(result))
                
            elif action == 'get_exercise_detail':
                exercise_id = text_data_json.get('exercise_id')
                
                # 获取习题详情
                exercise_detail = await self.get_exercise_detail(exercise_id)
                
                # 发送响应
                await self.send(text_data=json.dumps(exercise_detail))
        
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': str(e),
                'status': 'error'
            }))
    
    @database_sync_to_async
    def submit_exercise_attempt(self, exercise_id, user_answer):
        """
        提交习题尝试（同步函数，使用database_sync_to_async装饰器）
        """
        try:
            exercise = Exercise.objects.get(id=exercise_id)
            
            # 检查答案是否正确
            is_correct = False
            if exercise.type == 'single':
                is_correct = user_answer == exercise.answer
            elif exercise.type == 'multiple':
                # 多选题答案可能是列表形式
                if isinstance(user_answer, list):
                    user_answer_set = set(user_answer)
                    correct_answer_set = set(exercise.answer.split(','))
                    is_correct = user_answer_set == correct_answer_set
                else:
                    # 如果是字符串格式，按逗号分隔
                    user_answer_set = set(user_answer.split(','))
                    correct_answer_set = set(exercise.answer.split(','))
                    is_correct = user_answer_set == correct_answer_set
            
            # 创建或更新习题尝试记录
            attempt, created = ExerciseAttempt.objects.update_or_create(
                user=self.user,
                exercise=exercise,
                defaults={
                    'is_correct': is_correct,
                    'user_answer': str(user_answer),
                }
            )
            
            # 如果答案错误，将习题添加到错题集
            if not is_correct:
                UserMistakeCollection.objects.get_or_create(
                    user=self.user,
                    exercise=exercise
                )
            
            return {
                'is_correct': is_correct,
                'correct_answer': exercise.answer,
                'explanation': exercise.explanation,
                'status': 'success'
            }
            
        except Exercise.DoesNotExist:
            return {
                'error': '习题不存在',
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"提交习题尝试出错: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }
    
    @database_sync_to_async
    def get_exercise_detail(self, exercise_id):
        """
        获取习题详情（同步函数，使用database_sync_to_async装饰器）
        """
        try:
            exercise = Exercise.objects.get(id=exercise_id)
            
            # 获取用户之前的尝试
            previous_attempt = None
            if self.user.is_authenticated:
                try:
                    previous_attempt = ExerciseAttempt.objects.get(
                        user=self.user,
                        exercise=exercise
                    )
                except ExerciseAttempt.DoesNotExist:
                    pass
            
            # 准备选项
            options = {}
            if exercise.options and isinstance(exercise.options, str):
                try:
                    options = json.loads(exercise.options)
                except json.JSONDecodeError:
                    options = {}
                    
            # 构建响应数据
            response = {
                'id': exercise.id,
                'content': exercise.content,
                'type': exercise.type,
                'options': options,
                'status': 'success'
            }
            
            # 如果有之前的尝试，添加相关信息
            if previous_attempt:
                response.update({
                    'user_answer': previous_attempt.user_answer,
                    'is_correct': previous_attempt.is_correct,
                    'correct_answer': exercise.answer,
                    'explanation': exercise.explanation
                })
                
            return response
            
        except Exercise.DoesNotExist:
            return {
                'error': '习题不存在',
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"获取习题详情出错: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }


class AIExerciseConsumer(AsyncWebsocketConsumer):
    """
    处理AI生成习题相关WebSocket连接的异步消费者
    """
    async def connect(self):
        """
        建立WebSocket连接
        """
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # 从URL获取AI习题ID
        self.exercise_id = self.scope['url_route']['kwargs'].get('exercise_id')
        self.room_group_name = f'ai_exercise_{self.exercise_id}'
        
        # 加入房间组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """
        关闭WebSocket连接
        """
        if hasattr(self, 'room_group_name'):
            # 离开房间组
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """
        接收WebSocket消息
        """
        try:
            text_data_json = json.loads(text_data)
            action = text_data_json.get('action')
            
            if action == 'submit_ai_answer':
                exercise_id = text_data_json.get('exercise_id')
                user_answer = text_data_json.get('user_answer')
                
                # 处理AI习题答案提交
                result = await self.submit_ai_exercise_attempt(exercise_id, user_answer)
                
                # 发送响应
                await self.send(text_data=json.dumps(result))
                
            elif action == 'get_ai_exercise_detail':
                exercise_id = text_data_json.get('exercise_id')
                
                # 获取AI习题详情
                exercise_detail = await self.get_ai_exercise_detail(exercise_id)
                
                # 发送响应
                await self.send(text_data=json.dumps(exercise_detail))
        
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'error': str(e),
                'status': 'error'
            }))
    
    @database_sync_to_async
    def submit_ai_exercise_attempt(self, exercise_id, user_answer):
        """
        提交AI习题尝试（同步函数，使用database_sync_to_async装饰器）
        """
        try:
            ai_exercise = AIGeneratedExercise.objects.get(id=exercise_id)
            
            # 检查答案是否正确
            is_correct = False
            if ai_exercise.type == 'single':
                is_correct = user_answer == ai_exercise.answer
            elif ai_exercise.type == 'multiple':
                # 多选题答案可能是列表形式
                if isinstance(user_answer, list):
                    user_answer_set = set(user_answer)
                    correct_answer_set = set(ai_exercise.answer.split(','))
                    is_correct = user_answer_set == correct_answer_set
                else:
                    # 如果是字符串格式，按逗号分隔
                    user_answer_set = set(user_answer.split(','))
                    correct_answer_set = set(ai_exercise.answer.split(','))
                    is_correct = user_answer_set == correct_answer_set
            
            # 创建或更新AI习题尝试记录
            attempt, created = AIExerciseAttempt.objects.update_or_create(
                user=self.user,
                ai_exercise=ai_exercise,
                defaults={
                    'is_correct': is_correct,
                    'user_answer': str(user_answer),
                }
            )
            
            return {
                'is_correct': is_correct,
                'correct_answer': ai_exercise.answer,
                'explanation': ai_exercise.explanation,
                'status': 'success'
            }
            
        except AIGeneratedExercise.DoesNotExist:
            return {
                'error': 'AI习题不存在',
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"提交AI习题尝试出错: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            }
    
    @database_sync_to_async
    def get_ai_exercise_detail(self, exercise_id):
        """
        获取AI习题详情（同步函数，使用database_sync_to_async装饰器）
        """
        try:
            ai_exercise = AIGeneratedExercise.objects.get(id=exercise_id)
            
            # 获取用户之前的尝试
            previous_attempt = None
            if self.user.is_authenticated:
                try:
                    previous_attempt = AIExerciseAttempt.objects.get(
                        user=self.user,
                        ai_exercise=ai_exercise
                    )
                except AIExerciseAttempt.DoesNotExist:
                    pass
            
            # 准备选项
            options = {}
            if ai_exercise.options and isinstance(ai_exercise.options, str):
                try:
                    options = json.loads(ai_exercise.options)
                except json.JSONDecodeError:
                    options = {}
                    
            # 构建响应数据
            response = {
                'id': ai_exercise.id,
                'content': ai_exercise.content,
                'type': ai_exercise.type,
                'options': options,
                'status': 'success'
            }
            
            # 如果有之前的尝试，添加相关信息
            if previous_attempt:
                response.update({
                    'user_answer': previous_attempt.user_answer,
                    'is_correct': previous_attempt.is_correct,
                    'correct_answer': ai_exercise.answer,
                    'explanation': ai_exercise.explanation
                })
                
            return response
            
        except AIGeneratedExercise.DoesNotExist:
            return {
                'error': 'AI习题不存在',
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"获取AI习题详情出错: {str(e)}")
            return {
                'error': str(e),
                'status': 'error'
            } 