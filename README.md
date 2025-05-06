# 计算机考研智能题库系统 (基于 Django 和 大语言模型)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-4.x-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

## 简介

本项目是一个基于 Django 框架和先进的大语言模型 (LLM) 技术构建的 **计算机考研智能题库系统**。旨在为准备计算机专业研究生入学考试的学生提供一个高效、智能的学习和练习平台。系统不仅包含了传统的题库功能，还利用大模型的强大能力，提供智能化的题目解析、相似题目推荐、知识点问答等功能，辅助考生更深入地理解知识点和提高备考效率。

## 主要功能 ✨

* **📚 丰富的题库资源:**
    * 收录各大高校计算机考研历年真题、模拟题。
    * 支持按科目（如数据结构、计算机网络、操作系统、计算机组成原理）、章节、难度、题型（选择、填空、简答、算法）等多维度分类。
    * 管理员可方便地进行题目的增、删、改、查 (CRUD) 操作。
* **🧠 智能题目解析:**
    * 利用大语言模型为题目提供详细、易懂的步骤化解析。
    * 针对难题、易错题提供多种解题思路和技巧提示。
* **💡 智能问答与知识点讲解:**
    * 集成大模型，用户可直接针对题目或相关知识点进行提问，获得即时解答。
    * 提供关键知识点的概念解释、重点难点分析。
* **✍️ 在线练习与模拟考试:**
    * 支持多种练习模式：顺序练习、随机抽题、按知识点专项练习。
    * 提供模拟考试功能，模拟真实考试环境，支持计时和自动判分（选择、填空题）。
* **📊 学习进度与错题本:**
    * 记录用户的练习历史、答题情况、正确率。
    * 自动收集错题，生成个性化错题本，方便用户复习巩固。
* **🔍 智能搜索与推荐:**
    * 支持关键词搜索题目。
    * （可选）基于用户练习记录和 LLM 理解，推荐相关知识点和相似题目。
* **👤 用户管理:**
    * 支持用户注册、登录、个人信息管理。

## 技术栈 🛠️

* **后端:** Python 3.x, Django 4.x
* **数据库:** PostgreSQL / MySQL / SQLite (根据 `settings.py` 配置)
* **大语言模型 (LLM):** [在此处填写你使用的大模型名称或API，例如 OpenAI GPT-4, Google Gemini, 或是本地部署的模型]
* **前端 (示例):** HTML, CSS, JavaScript (可能使用 Bootstrap, Vue.js, React 等)
* **其他关键库:**
    * `djangorestframework` (如果提供了 API)
    * `requests` (用于调用 LLM API)
    * [其他你使用的库，例如 Celery 用于异步任务]

## 安装与部署 🚀

1.  **环境准备:**
    * 安装 Python (建议 3.8 或更高版本) 和 pip。
    * 安装 Git。
    * 安装数据库 (例如 PostgreSQL, MySQL)。

2.  **克隆仓库:**
    ```bash
    git clone [你的仓库地址]
    cd [项目目录名]
    ```

3.  **创建并激活虚拟环境:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **配置环境变量:**
    * 复制 `.env.example` 文件为 `.env`。
    * 根据你的环境修改 `.env` 文件中的配置，**至少需要配置**:
        * `SECRET_KEY`: Django 的密钥，可以使用 Django 的工具生成。
        * `DEBUG`: 开发环境设为 `True`，生产环境设为 `False`。
        * `DATABASE_URL`: 数据库连接信息 (例如: `postgres://user:password@host:port/dbname`)。
        * `LLM_API_KEY`: 你使用的大模型 API 密钥。
        * `LLM_API_ENDPOINT`: (如果需要) 大模型服务的 API 地址。
        * `ALLOWED_HOSTS`: 允许访问的主机列表。
    * *确保 `.env` 文件被添加到 `.gitignore` 中，不要提交到版本库！*

6.  **数据库迁移:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

7.  **创建超级用户 (用于后台管理):**
    ```bash
    python manage.py createsuperuser
    ```

8.  **运行开发服务器:**
    ```bash
    python manage.py runserver
    ```
    访问 `http://127.0.0.1:8000/` 查看应用。后台管理地址通常是 `http://127.0.0.1:8000/admin/`。

9.  **生产环境部署 (参考):**
