# import os

# # 日志配置
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'level': 'INFO', # Or set to 'DEBUG' for more detailed logs
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'loggers': {
#         '': { # This configures the root logger
#             'handlers': ['console'],
#             'level': 'INFO', # Or set to 'DEBUG'
#             'propagate': True,
#         },
#         'django': {
#             'handlers': ['console'],
#             'level': 'INFO', # You might want INFO or WARNING for Django's own logs
#             'propagate': False,
#         },
#         'courses': { # Specifically configure your 'courses' app logger
#             'handlers': ['console'],
#             'level': 'INFO', # Or set to 'DEBUG'
#             'propagate': False,
#         },
#     },
# }

# # 工具访问密钥
# TOOL_ACCESS_TOKEN = '78afhs87d9fn9a87an'

# # 大模型API密钥 (根据实际需要配置)
# # 实际使用时，建议通过环境变量设置或使用专门的密钥管理服务
# DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')  # 生产环境应使用环境变量
# GROK_API_KEY = os.environ.get('GROK_API_KEY', '')  # 生产环境应使用环境变量 