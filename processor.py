from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from anthropic import Anthropic
import os
from typing import List, Dict, Any
import json

class DocumentProcessor:
    def __init__(self, api_key, openai_api_key=None, collection_name="personal_knowledge"):
        self.client = Anthropic(api_key=api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        # 在实际项目中你可能需要替换为不同的嵌入模型
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        self.collection_name = collection_name
        self.db_path = "./data/chroma_db"
        
        # 如果已有向量库，则加载
        if os.path.exists(self.db_path):
            self.vectordb = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
        else:
            self.vectordb = None
    
    def load_document(self, file_path):
        """加载不同类型的文档"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.txt':
            loader = TextLoader(file_path)
        elif file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension in ['.docx', '.doc']:
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_extension}")
            
        documents = loader.load()
        return documents
    
    def process_document(self, file_path):
        """处理文档并添加到向量库"""
        documents = self.load_document(file_path)
        chunks = self.text_splitter.split_documents(documents)
        
        # 对每个chunk添加元数据
        for chunk in chunks:
            chunk.metadata["file_name"] = os.path.basename(file_path)
            chunk.metadata["file_path"] = file_path
        
        # 初始化或更新向量库
        if self.vectordb is None:
            self.vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_path,
                collection_name=self.collection_name
            )
        else:
            self.vectordb.add_documents(chunks)
            
        self.vectordb.persist()
        return len(chunks)
    
    def search(self, query, top_k=5):
        """搜索相关文档"""
        if self.vectordb is None:
            return []
            
        results = self.vectordb.similarity_search(query, k=top_k)
        return results
    
    def generate_answer(self, query, context_docs):
        """生成回答"""
        context = "\n\n".join([doc.page_content for doc in context_docs])
        
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": f"""
                我正在使用我的个人知识库。请基于以下内容回答我的问题。
                如果无法从以下内容中找到答案，请直接说明你不知道，不要编造信息。
                
                我的问题是: {query}
                
                参考内容:
                {context}
                """}
            ]
        )
        
        # 添加引用信息
        answer = response.content[0].text
        sources = [{"title": doc.metadata.get("file_name", "未知文档"), 
                   "path": doc.metadata.get("file_path", "")} 
                   for doc in context_docs]
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def parse_concepts_json(self, concepts_text):
        """尝试多种方法解析概念JSON"""
        # 首先尝试直接解析
        try:
            return json.loads(concepts_text)
        except:
            pass
        
        # 尝试提取 JSON 部分
        import re
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, concepts_text)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        # 如果无法解析，创建简单的结构
        # 尝试从文本中提取键值对
        concepts = {}
        lines = concepts_text.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                key = parts[0].strip().strip('"\'')
                value = parts[1].strip().strip('"\'')
                if key and value:
                    concepts[key] = value
        
        if concepts:
            return concepts
        
        # 实在不行，返回一个简单结构
        return {"未能解析": "无法从响应中提取结构化概念"}

    def extract_key_concepts(self, file_path):
        """提取文档中的关键概念"""
        documents = self.load_document(file_path)
        
        full_text = ""
        for doc in documents:
            full_text += doc.page_content
            
        # 使用前1500个字符来提取概念
        preview = full_text[:1500]
        
        response = self.client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=500,
            messages=[
                {"role": "user", "content": f"""
                请分析以下文本片段，提取5-10个关键概念或术语，以及它们的简短解释。
                返回格式必须是严格的JSON格式，包含概念名称和解释：
                
                {{
                    "概念1": "解释1",
                    "概念2": "解释2",
                    ...
                }}
                
                文本片段:
                {preview}
                """}
            ]
        )
        
        # 使用增强的解析函数
        concepts_text = response.content[0].text
        return concepts_text  # 返回原始文本，后续解析时再处理

    def extract_knowledge_relations(self, documents):
        """提取文档之间的知识关联"""
        # 获取所有文档的摘要和关键概念
        doc_concepts = {}
        relations = []
        
        for doc_path in documents:
            if not os.path.exists(doc_path):
                continue
            
            file_name = os.path.basename(doc_path)
            concepts_json = self.extract_key_concepts(doc_path)
            
            try:
                # 尝试解析JSON格式的概念
                concepts = json.loads(concepts_json)
                doc_concepts[file_name] = concepts
            except:
                continue
        
        # 使用Claude分析文档间的关系
        if len(doc_concepts) > 1:
            doc_pairs = [(name1, concepts1, name2, concepts2) 
                        for (name1, concepts1) in doc_concepts.items() 
                        for (name2, concepts2) in doc_concepts.items() 
                        if name1 != name2]
            
            for name1, concepts1, name2, concepts2 in doc_pairs:
                response = self.client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=500,
                    messages=[
                        {"role": "user", "content": f"""
                        请分析这两个文档的概念之间可能存在的关系:
                        
                        文档1: {name1}
                        概念: {json.dumps(concepts1, ensure_ascii=False)}
                        
                        文档2: {name2}
                        概念: {json.dumps(concepts2, ensure_ascii=False)}
                        
                        返回JSON格式的关系列表:
                        [
                            {{
                                "source_doc": "文档1名称",
                                "target_doc": "文档2名称",
                                "source_concept": "概念1",
                                "target_concept": "概念2",
                                "relation_type": "关系类型(相似/前置/扩展/示例/对立/包含)",
                                "strength": 0.8 // 关系强度0-1
                            }}
                        ]
                        
                        仅返回确定存在的关系，不要猜测。如果没有明确关系，返回空列表。
                        """}
                    ]
                )
                
                try:
                    new_relations = json.loads(response.content[0].text)
                    relations.extend(new_relations)
                except:
                    continue
                
        return relations

    def calculate_document_similarity(self, doc_paths):
        """计算文档间的相似度"""
        similarities = []
        
        # 为每个文档生成嵌入向量
        doc_embeddings = {}
        for path in doc_paths:
            if not os.path.exists(path):
                continue
            
            file_name = os.path.basename(path)
            docs = self.load_document(path)
            full_text = " ".join([doc.page_content for doc in docs])
            
            # 获取文档的嵌入向量
            embedding = self.vectordb._embedding_function.embed_documents([full_text])[0]
            doc_embeddings[file_name] = embedding
        
        # 计算文档间的相似度 - 避免导入问题的方法
        import numpy as np
        
        # 手动实现余弦相似度计算
        def cosine_sim(v1, v2):
            # 转为numpy数组
            v1_np = np.array(v1)
            v2_np = np.array(v2)
            
            # 计算余弦相似度
            dot_product = np.dot(v1_np, v2_np)
            norm_v1 = np.linalg.norm(v1_np)
            norm_v2 = np.linalg.norm(v2_np)
            
            # 避免除零错误
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            
            return dot_product / (norm_v1 * norm_v2)
        
        doc_names = list(doc_embeddings.keys())
        for i in range(len(doc_names)):
            for j in range(i+1, len(doc_names)):
                name1, name2 = doc_names[i], doc_names[j]
                vec1, vec2 = doc_embeddings[name1], doc_embeddings[name2]
                
                sim_score = float(cosine_sim(vec1, vec2))
                
                if sim_score > 0.5:  # 只保留相似度较高的关系
                    similarities.append({
                        "source": name1,
                        "target": name2,
                        "strength": sim_score,
                        "type": "similar"
                    })
        
        return similarities