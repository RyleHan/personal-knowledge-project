# 个人知识库增强剂
![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)


一个基于AI的个人知识管理系统，能够智能处理和检索您的文档，帮助您更快地找到信息。

## 功能特点

- 🔍 **语义搜索**：基于向量数据库的高级搜索，找到真正相关的内容
- 🤖 **AI生成回答**：基于您的文档智能生成答案
- 📊 **自动提取概念**：识别文档中的关键概念和术语
- 📚 **多格式支持**：处理PDF、Word文档和文本文件
- 💡 **知识关联**：发现文档之间的隐藏联系

## 技术架构

- **前端**：Streamlit
- **后端**：FastAPI
- **AI模型**：Claude 3.7 Sonnet
- **向量存储**：ChromaDB
- **文档处理**：LangChain

## 快速开始

### 设置环境

1. 克隆代码库：
   ```
   git clone https://github.com/RyleHan/personal-knowledge-enhancer.git
   cd personal-knowledge-enhancer
   ```

2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

3. 设置API密钥：
   ```
   export OPENAI_API_KEY=your_openai_api_key_here
   export ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

### 启动应用

运行启动脚本：
```
chmod +x run.sh
./run.sh
```

或者分别启动后端和前端：
```
# 终端1: 启动后端
uvicorn backend:app --reload --port 8000

# 终端2: 启动前端
streamlit run app.py
或者
streamlit run app.py --server.headless true
```

然后在浏览器中访问 http://localhost:8501

## 系统架构图

```
用户 → Streamlit前端 → FastAPI后端 → 文档处理器 → ChromaDB向量库 → Claude API
```

## 未来规划

- 添加文档间关系可视化
- 实现个性化学习路径推荐
- 支持更多文件格式（如PPT、HTML等）
- 添加协作功能

## 📜 版权声明

本项目由 [Erhan Lai](https://github.com/RyleHan/personal-knowledge-project) 独立设计与开发，版权所有 © 2025。

本项目遵循 [CC BY-NC-ND 4.0 License](https://creativecommons.org/licenses/by-nc-nd/4.0/)，禁止用于商业用途与改编创作，转载请注明出处。
