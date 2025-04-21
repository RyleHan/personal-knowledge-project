from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from anthropic import Anthropic
import os
from typing import List, Dict, Any

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
                返回格式为JSON格式，包含概念名称和解释。
                
                文本片段:
                {preview}
                """}
            ]
        )
        
        return response.content[0].text