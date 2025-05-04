import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network
import tempfile
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# 检查是否需要添加兼容性补丁
if not hasattr(np, 'alltrue') and hasattr(np, 'all'):
    np.alltrue = np.all
    print("已应用 NumPy 2.0 兼容性补丁")

matplotlib.use('Agg')  # 非交互式后端

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
tab1, tab2, tab3, tab4 = st.tabs(["📁 上传文档", "🔍 搜索知识", "📚 知识库管理", "🔄 知识关联可视化"])

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

# 知识关联可视化标签页
with tab4:
    st.header("知识关联可视化")
    
    # 控制面板
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("可视化设置")
        
        # 过滤选项
        relation_types = st.multiselect(
            "关系类型",
            ["相似", "前置", "扩展", "示例", "对立", "包含"],
            default=["相似", "包含"]
        )
        
        # 布局选项
        layout = st.selectbox(
            "布局算法",
            ["force", "hierarchical"],
            index=0
        )
        
        # 演示模式选项
        demo_mode = st.checkbox("演示模式", value=False, help="使用示例数据生成图谱")
        
        # 控制按钮
        refresh = st.button("刷新知识图谱")
    
    # 主要图谱区域
    with col2:
        if demo_mode:
            # 生成演示数据
            demo_nodes = [
                {"id": "doc1.pdf", "name": "人工智能导论", "type": "document", "size": 15},
                {"id": "doc2.pdf", "name": "机器学习基础", "type": "document", "size": 15},
                {"id": "doc1_AI", "name": "人工智能", "type": "concept", "size": 10},
                {"id": "doc1_ML", "name": "机器学习", "type": "concept", "size": 10},
                {"id": "doc1_DL", "name": "深度学习", "type": "concept", "size": 10},
                {"id": "doc2_ML", "name": "机器学习算法", "type": "concept", "size": 10},
                {"id": "doc2_SVM", "name": "支持向量机", "type": "concept", "size": 10}
            ]
            
            demo_links = [
                {"source": "doc1.pdf", "target": "doc1_AI", "type": "contains", "value": 0.8},
                {"source": "doc1.pdf", "target": "doc1_ML", "type": "contains", "value": 0.7},
                {"source": "doc1.pdf", "target": "doc1_DL", "type": "contains", "value": 0.6},
                {"source": "doc2.pdf", "target": "doc2_ML", "type": "contains", "value": 0.8},
                {"source": "doc2.pdf", "target": "doc2_SVM", "type": "contains", "value": 0.7},
                {"source": "doc1.pdf", "target": "doc2.pdf", "type": "similar", "value": 0.6},
                {"source": "doc1_ML", "target": "doc2_ML", "type": "similar", "value": 0.9},
                {"source": "doc1_ML", "target": "doc2_SVM", "type": "prerequisite", "value": 0.7},
                {"source": "doc1_AI", "target": "doc1_ML", "type": "contains", "value": 0.8},
                {"source": "doc1_ML", "target": "doc1_DL", "type": "prerequisite", "value": 0.8}
            ]
            
            # 直接在这里设置图谱数据变量，避免通过会话状态
            graph_data = {"nodes": demo_nodes, "links": demo_links}
            
            st.write(f"演示模式已启用 - 节点数量: {len(demo_nodes)}, 连接数量: {len(demo_links)}")
            
            # 检查数据类型
            st.write("节点数据类型:", type(graph_data["nodes"]))
            st.write("连接数据类型:", type(graph_data["links"]))
            
            # 显示第一个节点和连接(如果有)
            if graph_data["nodes"]:
                st.write("示例节点:", graph_data["nodes"][0])
            if graph_data["links"]:
                st.write("示例连接:", graph_data["links"][0])
        elif refresh or "knowledge_graph" not in st.session_state:
            with st.spinner("正在生成知识图谱..."):
                try:
                    response = requests.get(f"{API_URL}/knowledge-graph")
                    
                    if response.status_code == 200:
                        graph_data = response.json()
                        st.session_state.knowledge_graph = graph_data
                        
                        # 调试输出
                        st.write(f"获取到的节点数量: {len(graph_data['nodes'])}")
                        st.write(f"获取到的连接数量: {len(graph_data['links'])}")
                    else:
                        st.error(f"获取知识图谱失败: {response.text}")
                        st.session_state.knowledge_graph = {"nodes": [], "links": []}
                except Exception as e:
                    st.error(f"连接后端失败: {str(e)}")
                    st.session_state.knowledge_graph = {"nodes": [], "links": []}
        
        # 生成并显示网络图
        if hasattr(st.session_state, "knowledge_graph"):
            graph_data = st.session_state.knowledge_graph
            
            if not graph_data["nodes"]:
                st.info("没有足够的文档或关系来构建知识图谱。请上传更多文档。")
            else:
                # 显示原始数据
                st.write(f"原始节点数量: {len(graph_data['nodes'])}")
                st.write(f"原始连接数量: {len(graph_data['links'])}")
                
                # 调试 - 查看关系类型的实际值
                unique_types = set(link.get("type", "unknown") for link in graph_data["links"])
                st.write("实际关系类型:", list(unique_types))
                
                # 确保关系类型匹配
                # 使用更宽松的匹配逻辑 - 包含而非精确匹配
                filtered_links = []
                for link in graph_data["links"]:
                    link_type = link.get("type", "").lower()
                    # 检查是否至少有一个选择的关系类型包含在当前链接类型中
                    for selected_type in relation_types:
                        if selected_type.lower() in link_type:
                            filtered_links.append(link)
                            break
                
                # 如果筛选后连接为空，使用所有连接
                if not filtered_links:
                    st.warning("使用选择的关系类型无法筛选出任何连接，显示所有连接")
                    filtered_links = graph_data["links"]
                
                # 创建节点集合
                used_nodes = set()
                for link in filtered_links:
                    used_nodes.add(link["source"])
                    used_nodes.add(link["target"])
                
                filtered_nodes = [node for node in graph_data["nodes"] 
                                if node["id"] in used_nodes]
                
                # 显示筛选后数据的数量
                st.write(f"筛选后节点数量: {len(filtered_nodes)}")
                st.write(f"筛选后连接数量: {len(filtered_links)}")
                
                if filtered_nodes:
                    st.write("使用NetworkX和Matplotlib生成图谱...")
                    
                    # 创建NetworkX图
                    G = nx.Graph()
                    
                    # 添加节点
                    for node in filtered_nodes:
                        G.add_node(node["id"], type=node["type"], name=node["name"])
                    
                    # 添加边
                    for link in filtered_links:
                        if link["source"] in G.nodes() and link["target"] in G.nodes():
                            G.add_edge(link["source"], link["target"], 
                                      type=link.get("type", "关联"),
                                      weight=link.get("value", 0.5))
                    
                    # 创建节点颜色列表
                    node_colors = []
                    for node in G.nodes():
                        if G.nodes[node].get("type") == "document":
                            node_colors.append("#5DA5DA")  # 文档节点蓝色
                        else:
                            node_colors.append("#FAA43A")  # 概念节点橙色
                    
                    # 创建节点大小列表
                    node_sizes = []
                    for node in G.nodes():
                        if G.nodes[node].get("type") == "document":
                            node_sizes.append(800)  # 文档节点大一些
                        else:
                            node_sizes.append(500)  # 概念节点小一些
                    
                    # 创建边颜色列表
                    edge_colors = []
                    for u, v, d in G.edges(data=True):
                        if d.get("type") == "similar":
                            edge_colors.append("#60BD68")  # 相似关系绿色
                        elif d.get("type") == "prerequisite":
                            edge_colors.append("#F17CB0")  # 前置关系粉色
                        elif d.get("type") == "extension":
                            edge_colors.append("#B2912F")  # 扩展关系棕色
                        elif d.get("type") == "example":
                            edge_colors.append("#B276B2")  # 示例关系紫色
                        elif d.get("type") == "opposite":
                            edge_colors.append("#D85F5F")  # 对立关系红色
                        elif d.get("type") == "contains":
                            edge_colors.append("#4D4D4D")  # 包含关系黑色
                        else:
                            edge_colors.append("#666666")  # 其他关系灰色
                    
                    # 计算边宽度
                    edge_widths = []
                    for u, v, d in G.edges(data=True):
                        weight = d.get("weight", 0.5)
                        edge_widths.append(weight * 3)
                    
                    # 创建图形
                    plt.figure(figsize=(12, 8))
                    
                    # 选择布局
                    if layout == "hierarchical":
                        pos = nx.spring_layout(G, seed=42)
                    else:
                        pos = nx.spring_layout(G, seed=42)
                    
                    # 绘制节点
                    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
                    
                    # 绘制边
                    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, alpha=0.7)
                    
                    # 绘制标签
                    nx.draw_networkx_labels(G, pos, font_size=10, font_family="sans-serif")
                    
                    # 调整布局
                    plt.axis("off")
                    plt.tight_layout()
                    
                    # 显示图形
                    st.pyplot(plt)
                    
                    # 也显示节点和边的列表，作为备份
                    with st.expander("查看节点和关系列表"):
                        # 显示节点列表
                        st.subheader("知识节点表格")
                        nodes_df = pd.DataFrame(filtered_nodes if filtered_nodes else graph_data["nodes"])
                        st.dataframe(nodes_df)
                        
                        # 显示关系列表
                        st.subheader("知识关联表格")
                        links_df = pd.DataFrame(filtered_links if filtered_links else graph_data["links"])
                        st.dataframe(links_df)
                else:
                    st.info("筛选后没有节点可显示。请选择其他关系类型或添加更多文档。")
                
                # 添加知识图谱解释
                with st.expander("📖 如何阅读这个知识图谱"):
                    st.markdown("""
                    **节点类型**:
                    - 🔵 蓝色: 文档
                    - 🟠 橙色: 概念或术语
                    
                    **连接类型**:
                    - 🟢 绿色: 相似关系
                    - 💗 粉色: 前置知识
                    - 🟤 棕色: 扩展知识
                    - 🟣 紫色: 示例说明
                    - 🔴 红色: 对立概念
                    - ⚫ 黑色: 包含关系
                    
                    **交互提示**:
                    - 鼠标悬停在节点或连接上可查看详细信息
                    - 拖动节点可调整布局
                    - 滚轮缩放查看详情
                    - 双击节点聚焦相关内容
                    """)

# 页脚
st.divider()
st.markdown(f"© {datetime.now().year} 个人知识库增强剂 | 上次更新: {datetime.now().strftime('%Y-%m-%d')}")