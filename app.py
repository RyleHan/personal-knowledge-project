import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import datetime

# 配置页面
st.set_page_config(
    page_title="个人知识库增强剂",
    page_icon="🧠",
    layout="wide",
)

# API端点
API_URL = "http://localhost:8000"

# 设置API密钥
if "api_key_set" not in st.session_state:
    st.session_state.api_key_set = False

# 标题和介绍
st.title("🧠 个人知识库增强剂")
st.markdown("""
这个工具可以帮你:
- 📚 管理和组织个人文档
- 🔍 智能搜索文档内容
- 💡 发现文档间的关联
- 📊 可视化知识结构
""")

# 侧边栏 - 设置API密钥
with st.sidebar:
    st.header("⚙️ 设置")
    
    api_key = st.text_input("输入Anthropic API密钥", type="password")
    if st.button("保存API密钥"):
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
            st.session_state.api_key_set = True
            st.success("API密钥已保存!")
        else:
            st.error("请输入有效的API密钥")
    
    st.divider()
    st.markdown("### 📈 知识库统计")
    try:
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            docs = response.json().get("documents", [])
            st.metric("文档总数", len(docs))
            if docs:
                total_size = sum(doc["size_kb"] for doc in docs)
                st.metric("总容量", f"{total_size:.2f} KB")
        else:
            st.warning("无法获取知识库统计")
    except:
        st.warning("后端服务未启动")

# 创建标签页
tab1, tab2, tab3 = st.tabs(["📁 上传文档", "🔍 搜索知识", "📚 知识库管理"])

# 上传文档标签页
with tab1:
    st.header("上传新文档")
    
    uploaded_file = st.file_uploader("选择一个文档 (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    
    if uploaded_file and st.button("处理文档"):
        with st.spinner("正在处理文档..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file, "application/octet-stream")}
                response = requests.post(f"{API_URL}/upload", files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"文档 '{result['filename']}' 成功处理! 处理了 {result['chunks_processed']} 个文本块。")
                    
                    # 显示提取的关键概念
                    st.subheader("文档关键概念")
                    try:
                        concepts = json.loads(result['key_concepts'])
                        for concept, description in concepts.items():
                            st.markdown(f"**{concept}**: {description}")
                    except:
                        st.text(result['key_concepts'])
                else:
                    st.error(f"处理失败: {response.text}")
            except Exception as e:
                st.error(f"发生错误: {str(e)}")

# 搜索知识标签页
with tab2:
    st.header("智能搜索你的知识库")
    
    query = st.text_input("输入你的问题")
    
    if query and st.button("搜索"):
        with st.spinner("正在搜索相关信息..."):
            try:
                response = requests.post(
                    f"{API_URL}/search",
                    data={"query": query}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    st.subheader("🤖 回答")
                    st.markdown(result["answer"])
                    
                    st.subheader("📑 信息来源")
                    for i, source in enumerate(result["sources"], 1):
                        st.markdown(f"{i}. **{source['title']}**")
                else:
                    st.error(f"搜索失败: {response.text}")
            except Exception as e:
                st.error(f"发生错误: {str(e)}")

# 知识库管理标签页
with tab3:
    st.header("管理你的文档")
    
    if st.button("刷新文档列表"):
        st.session_state.refresh_docs = True
    
    try:
        with st.spinner("获取文档列表..."):
            response = requests.get(f"{API_URL}/documents")
            
            if response.status_code == 200:
                docs = response.json().get("documents", [])
                
                if docs:
                    # 创建数据表格
                    df = pd.DataFrame(docs)
                    df.columns = ["文件名", "路径", "大小(KB)"]
                    st.dataframe(df)
                else:
                    st.info("知识库中还没有文档，请先上传文档。")
            else:
                st.error("获取文档列表失败")
    except Exception as e:
        st.error(f"无法连接到后端服务: {str(e)}")

# 页脚
st.divider()
st.markdown(f"© {datetime.now().year} 个人知识库增强剂 | 上次更新: {datetime.now().strftime('%Y-%m-%d')}")