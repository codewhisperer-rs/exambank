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
    * 框架: **Django 5.2** (原生 ASGI 异步视图 + 异步 ORM)
    * 异步通信: **Django Channels 3.0.5** — 基于 WebSocket 的实时双向通信（习题提交、AI 助教流式对话）
    * ASGI 服务器: **Daphne 3.0.2** (WebSocket/HTTP2)；生产环境亦可使用 **Gunicorn 22.0.0**
    * 异步 HTTP 客户端: **httpx**、**aiohttp** — 用于异步调用大语言模型 API
    * Channel Layer: InMemoryChannelLayer（开发）/ **channels-redis** 4.0.0（生产）

* **大语言模型 (LLM):**
    * **DeepSeek API** (`deepseek-chat`) — 知识点提取、AI 习题生成与推荐
    * **Grok API** (xAI, `grok-3`) — 知识点提取、AI 习题生成与推荐
    * 调用方式: 带重试机制的异步调用（`httpx` / `aiohttp`）

* **数据库 (Database):**
    * **SQLite** (开发/部署默认) — 通过 Django ORM 操作

* **前端 (Frontend):**
    * **Django 模板引擎** — 服务端渲染 HTML 页面
    * **JavaScript** (原生 JS + WebSocket API) — 实时交互、WebSocket 通信
    * **Markdown 渲染**: `markdown`、`django-markdownify`、`pymdown-extensions` — 在页面中渲染富文本内容

* **AI 助教前端 (AI Chat Assistant Frontend):**
    * **Next.js** (React 框架) — 独立的 AI 对话界面服务（端口 3000）
    * 包管理器: **pnpm**
    * 运行时: **Node.js 19**

* **部署 & 运维 (DevOps):**
    * 容器化: **Docker** + **Docker Compose** — 将 Django 后端与 Next.js 前端打包为统一镜像
    * 多阶段构建: Node.js 构建阶段 + Python 运行阶段
    * 环境变量管理: **python-dotenv**

* **其他关键依赖 (Other Key Libraries):**
    * `Pillow` — 书籍封面等图片处理
    * `asgiref` — Django 异步 / 同步桥接工具 (`sync_to_async`, `async_to_sync`)
    * `requests` — 同步 HTTP 请求备用
    * `markdownify` — HTML ↔ Markdown 转换

## 安装部署

**1. 环境准备:**
* 确保已安装 **Python 3.12** 及 `pip` 包管理器。
* 推荐使用虚拟环境 (如 `venv`) 来隔离项目依赖。
    ```bash
    conda create -n exambank python==3.12
    conda activate exambank
    pip install -r requrements.txt
    ```

**2. 获取代码:**
```bash
git clone <your-repository-url>
cd <repository-directory-name>
