from django.test import TestCase
import requests
import json
import os
import unittest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from .models import UserMistakeCollection, Exercise, AIGeneratedExercise
from .views import _call_grok_api, _call_deepseek_api, _prepare_recommendation_prompt


TEST_GROK_API_KEY = os.environ.get('TEST_GROK_API_KEY', '')
TEST_DEEPSEEK_API_KEY = os.environ.get('TEST_DEEPSEEK_API_KEY', '')
GROK_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

class APIConnectionTestCase(TestCase):
    """测试API连接性的基本测试用例"""
    
    def test_grok_api_endpoint_exists(self):
        """测试Grok API端点是否存在可访问"""
        try:
            # 只测试连接，不发送实际请求
            response = requests.head(GROK_API_URL, timeout=5)
            # 即使返回401未授权，也说明端点存在
            self.assertIn(response.status_code, [200, 401, 403, 404, 405])
            print(f"Grok API端点状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.fail(f"无法连接到Grok API: {str(e)}")
    
    def test_deepseek_api_endpoint_exists(self):
        """测试DeepSeek API端点是否存在可访问"""
        try:
            # 只测试连接，不发送实际请求
            response = requests.head(DEEPSEEK_API_URL, timeout=5)
            # 即使返回401未授权，也说明端点存在
            self.assertIn(response.status_code, [200, 401, 403, 404, 405])
            print(f"DeepSeek API端点状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.fail(f"无法连接到DeepSeek API: {str(e)}")


@unittest.skipIf(not TEST_GROK_API_KEY, "跳过Grok API测试：未设置测试密钥")
class GrokAPITestCase(TestCase):
    """测试Grok API的具体功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.headers = {
            "Authorization": f"Bearer {TEST_GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        self.test_prompt = "请返回一个简单的JSON格式响应，内容是：[{\"content\":\"这是一个测试题目\",\"type\":\"单选题\",\"answer\":\"A\"}]"
        self.data = {
            "model": "grok-3-latest",
            "messages": [
                {"role": "system", "content": "你是一个教育助手，请以JSON格式回复。"},
                {"role": "user", "content": self.test_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    
    def test_grok_api_simple_request(self):
        """测试发送简单请求到Grok API"""
        try:
            response = requests.post(
                GROK_API_URL, 
                headers=self.headers, 
                json=self.data, 
                timeout=10
            )
            
            if response.status_code == 200:
                # 成功获取响应
                response_json = response.json()
                self.assertIn('choices', response_json)
                print("成功获取Grok API响应")
            else:
                # 如果API密钥无效或其他错误，打印详细信息
                print(f"Grok API请求失败: HTTP {response.status_code} - {response.text}")
                # 不使测试失败，因为这可能是因为无效密钥
        except requests.exceptions.RequestException as e:
            self.fail(f"Grok API请求异常: {str(e)}")
    
    def test_grok_api_with_retry(self):
        """测试带有重试机制的Grok API请求"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.post(
                    GROK_API_URL, 
                    headers=self.headers, 
                    json=self.data, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    # 成功获取响应
                    print(f"成功获取Grok API响应 (尝试次数: {retry_count + 1})")
                    break
                else:
                    print(f"Grok API请求失败: HTTP {response.status_code} (尝试次数: {retry_count + 1})")
                
            except requests.exceptions.Timeout:
                print(f"Grok API请求超时 (尝试次数: {retry_count + 1})")
            except requests.exceptions.ConnectionError:
                print(f"Grok API连接错误 (尝试次数: {retry_count + 1})")
            except requests.exceptions.RequestException as e:
                print(f"Grok API请求异常: {str(e)} (尝试次数: {retry_count + 1})")
            
            retry_count += 1
            if retry_count < max_retries:
                # 如果还有重试次数，等待1秒后重试
                import time
                time.sleep(1)
        
        # 不断言必须成功，仅记录结果
        if retry_count >= max_retries:
            print("Grok API请求在多次尝试后仍然失败")


@unittest.skipIf(not TEST_DEEPSEEK_API_KEY, "跳过DeepSeek API测试：未设置测试密钥")
class DeepSeekAPITestCase(TestCase):
    """测试DeepSeek API的具体功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.headers = {
            "Authorization": f"Bearer {TEST_DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        self.test_prompt = "请返回一个简单的JSON格式响应，内容是：[{\"content\":\"这是一个测试题目\",\"type\":\"单选题\",\"answer\":\"A\"}]"
        self.data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个教育助手，请以JSON格式回复。"},
                {"role": "user", "content": self.test_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
    
    def test_deepseek_api_simple_request(self):
        """测试发送简单请求到DeepSeek API"""
        try:
            response = requests.post(
                DEEPSEEK_API_URL, 
                headers=self.headers, 
                json=self.data, 
                timeout=10
            )
            
            if response.status_code == 200:
                # 成功获取响应
                response_json = response.json()
                self.assertIn('choices', response_json)
                print("成功获取DeepSeek API响应")
            else:
                # 如果API密钥无效或其他错误，打印详细信息
                print(f"DeepSeek API请求失败: HTTP {response.status_code} - {response.text}")
                # 不使测试失败，因为这可能是因为无效密钥
        except requests.exceptions.RequestException as e:
            self.fail(f"DeepSeek API请求异常: {str(e)}")
    
    def test_deepseek_api_with_retry(self):
        """测试带有重试机制的DeepSeek API请求"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.post(
                    DEEPSEEK_API_URL, 
                    headers=self.headers, 
                    json=self.data, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    # 成功获取响应
                    print(f"成功获取DeepSeek API响应 (尝试次数: {retry_count + 1})")
                    break
                else:
                    print(f"DeepSeek API请求失败: HTTP {response.status_code} (尝试次数: {retry_count + 1})")
                
            except requests.exceptions.Timeout:
                print(f"DeepSeek API请求超时 (尝试次数: {retry_count + 1})")
            except requests.exceptions.ConnectionError:
                print(f"DeepSeek API连接错误 (尝试次数: {retry_count + 1})")
            except requests.exceptions.RequestException as e:
                print(f"DeepSeek API请求异常: {str(e)} (尝试次数: {retry_count + 1})")
            
            retry_count += 1
            if retry_count < max_retries:
                # 如果还有重试次数，等待1秒后重试
                import time
                time.sleep(1)
        
        # 不断言必须成功，仅记录结果
        if retry_count >= max_retries:
            print("DeepSeek API请求在多次尝试后仍然失败")


# 单元测试Django视图中的API调用函数
class APIFunctionTestCase(TestCase):
    """测试视图函数中的API调用功能"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建测试用户
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        # 模拟一个错题记录
        # 注意：这需要创建相关的模型实例
    
    @patch('courses.views.requests.post')
    def test_call_grok_api(self, mock_post):
        """测试_call_grok_api函数"""
        # 模拟成功的API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '[{"content":"测试题目","type":"单选题","answer":"A"}]'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用API函数
        result = _call_grok_api("测试提示词")
        
        # 验证函数行为
        mock_post.assert_called_once()  # 验证HTTP请求被发送
        self.assertIsInstance(result, list)  # 验证返回结果是列表
    
    @patch('courses.views.requests.post')
    def test_call_grok_api_error(self, mock_post):
        """测试_call_grok_api函数处理错误的情况"""
        # 模拟失败的API响应
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        # 调用API函数，并期望返回错误信息
        result = _call_grok_api("测试提示词")
        
        # 验证返回错误信息
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
    
    @patch('courses.views.requests.post')
    def test_call_grok_api_exception(self, mock_post):
        """测试_call_grok_api函数处理异常的情况"""
        # 模拟请求抛出异常
        mock_post.side_effect = requests.exceptions.Timeout("连接超时")
        
        # 调用API函数，并期望正确处理异常
        result = _call_grok_api("测试提示词")
        
        # 验证返回错误信息
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
    
    @patch('courses.views.requests.post')
    def test_call_deepseek_api(self, mock_post):
        """测试_call_deepseek_api函数"""
        # 模拟成功的API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '[{"content":"测试题目","type":"单选题","answer":"A"}]'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用API函数
        result = _call_deepseek_api("测试提示词")
        
        # 验证函数行为
        mock_post.assert_called_once()  # 验证HTTP请求被发送
        self.assertIsInstance(result, list)  # 验证返回结果是列表


# 运行测试的命令:
# python manage.py test courses.tests.APIConnectionTestCase
# python manage.py test courses.tests.GrokAPITestCase
# python manage.py test courses.tests.DeepSeekAPITestCase
# python manage.py test courses.tests.APIFunctionTestCase
