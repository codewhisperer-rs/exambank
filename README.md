# 计算机考研智能题库系统 (基于 Django 和 大语言模型)

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)


## 简介

本项目是一个基于 **Python 3.12** 和 **Django 5.2** 构建的现代化、**异步支持**的智能学习辅导系统，专为准备**计算机专业研究生入学考试**的用户设计。系统深度融合了**知识图谱**、**个性化错题管理**，并利用**大语言模型 (LLM)** 提供**智能知识点提取**、**AI 习题生成与推荐**、**AI 助教**等功能，旨在打造一站式、高效、智能的学习与备考平台。

## 主要功能

* **📚 课程知识图谱:**
    * 提供 **数据结构**、**计算机网络**、**计算机组成原理**、**操作系统** 四门核心课程的结构化知识图谱。
    * 帮助用户系统梳理知识体系，进行关联性学习。

* **❌ 个性化错题集:**
    * 自动记录用户练习中的错题，**每个用户的错题记录相互独立**。
    * 支持错题回顾、筛选与管理，方便进行针对性复习。

* **💡 智能知识点提取:**
    * 利用 **大语言模型 (LLM)** 分析用户提交的错题内容。
    * 精准定位并提取错题背后关联的**核心知识点**。

* **✍️ AI 习题服务:**
    * **智能生成:** 基于提取的知识点或用户具体的错题，动态生成新的、相关的练习题目。
    * **智能推荐:** 根据用户的错题历史和薄弱环节，直接推荐或生成针对性的练习题进行强化。
    * **AI 习题库:** 统一存储和管理所有由 AI 生成的习题，方便用户随时练习。

* **🤖 AI 助教:**
    * 提供基于所覆盖课程内容的 **交互式对话问答** 功能。
    * 用户可以就学习中遇到的概念、题目理解等问题与 AI 进行对话，获得即时辅导。

* **⚡ 异步架构:**
    * 充分利用 **Django 5.2** 的原生异步视图和 ORM 支持，提升系统在高并发场景下的性能和响应速度。

## 技术栈

* **后端 (Backend):**
    * 语言: **Python 3.12**
    * 框架: **Django 5.2** (启用 ASGI 异步模式)
* **大语言模型 (LLM):**
    * 集成用于: 知识点提取、习题生成/推荐、AI 助教问答。
    * *(可在此处注明具体使用的模型或服务 API，例如：OpenAI API, Google Gemini API, 或其他本地/云端模型)*
* **数据库 (Database):**
    * *(在此处注明项目使用的数据库，如：PostgreSQL, MySQL, SQLite)*
* **前端 (Frontend):**
    * *(在此处注明使用的前端技术栈，如：HTML, CSS, JavaScript, React, Vue 等)*
* **其他 (Others):**
    * *(可列出其他关键依赖库或技术，如：Celery (如果用于后台任务), Redis (如果用于缓存或队列) 等)*

## 安装部署

**1. 环境准备:**
* 确保已安装 **Python 3.12** 及 `pip` 包管理器。
* 推荐使用虚拟环境 (如 `venv`) 来隔离项目依赖。
    ```bash
    python -m venv venv
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```
* *(根据需要安装数据库服务，如 PostgreSQL, MySQL)*

**2. 获取代码:**
```bash
git clone <your-repository-url>
cd <repository-directory-name>
