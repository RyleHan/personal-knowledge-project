from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
from processor import DocumentProcessor
import json
from typing import List

app = FastAPI(title="个人知识库增强剂")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用环境变量获取API密钥
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your_api_key_here")
document_processor = DocumentProcessor(api_key=ANTHROPIC_API_KEY)

# 确保数据目录存在
os.makedirs("./data/uploads", exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传文档并处理"""
    try:
        # 生成唯一文件名并保存
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"./data/uploads/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 处理文档
        chunks_count = document_processor.process_document(file_path)
        
        # 提取关键概念
        concepts = document_processor.extract_key_concepts(file_path)
        
        return {
            "filename": file.filename,
            "stored_path": file_path,
            "chunks_processed": chunks_count,
            "key_concepts": concepts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")

@app.post("/search")
async def search(query: str = Form(...)):
    """搜索知识库"""
    try:
        results = document_processor.search(query)
        if not results:
            return {"answer": "未找到相关信息", "sources": []}
        
        response = document_processor.generate_answer(query, results)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索时出错: {str(e)}")

@app.get("/documents")
async def list_documents():
    """列出所有已上传的文档"""
    try:
        files = []
        uploads_dir = "./data/uploads"
        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                file_path = os.path.join(uploads_dir, filename)
                if os.path.isfile(file_path):
                    files.append({
                        "filename": filename,
                        "path": file_path,
                        "size_kb": round(os.path.getsize(file_path) / 1024, 2)
                    })
        return {"documents": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表时出错: {str(e)}")

@app.get("/knowledge-graph")
async def get_knowledge_graph():
    """获取知识图谱数据"""
    try:
        uploads_dir = "./data/uploads"
        if not os.path.exists(uploads_dir):
            return {"nodes": [], "links": []}
            
        # 获取所有文档路径
        doc_paths = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) 
                    if os.path.isfile(os.path.join(uploads_dir, f))]
        
        # 即使没有关系，也至少返回文档节点
        nodes = []
        for path in doc_paths:
            doc_name = os.path.basename(path)
            nodes.append({
                "id": doc_name,
                "name": doc_name,
                "type": "document",
                "size": 15
            })
        
        # 调试信息
        print(f"找到了 {len(doc_paths)} 个文档")
        
        # 尝试提取概念 - 简化版，确保每个文档至少有一个概念
        links = []
        for path in doc_paths:
            try:
                doc_name = os.path.basename(path)
                
                # 提取文档的关键概念
                concepts_json = document_processor.extract_key_concepts(path)
                
                try:
                    # 解析JSON
                    concepts = json.loads(concepts_json)
                    # 只处理字典形式的概念数据
                    if isinstance(concepts, dict):
                        # 为每个概念创建节点和关系
                        for concept, description in list(concepts.items())[:3]:  # 只取前3个概念
                            # 添加概念节点
                            concept_id = f"{doc_name}_{concept}"
                            nodes.append({
                                "id": concept_id,
                                "name": concept,
                                "type": "concept",
                                "document": doc_name,
                                "size": 10
                            })
                            
                            # 添加文档到概念的关系
                            links.append({
                                "source": doc_name,
                                "target": concept_id,
                                "type": "contains",
                                "value": 0.7
                            })
                except Exception as e:
                    print(f"解析文档 {doc_name} 的概念时出错: {str(e)}")
                    continue
            except Exception as e:
                print(f"处理文档 {path} 时出错: {str(e)}")
                continue
        
        # 如果有多个文档，尝试添加简单的文档间相似关系
        if len(doc_paths) > 1:
            try:
                similarity_relations = document_processor.calculate_document_similarity(doc_paths)
                for relation in similarity_relations:
                    links.append({
                        "source": relation["source"],
                        "target": relation["target"],
                        "type": "similar",
                        "value": relation["strength"]
                    })
            except Exception as e:
                print(f"计算文档相似度时出错: {str(e)}")
        
        # 返回结果，即使图谱可能很简单
        return {"nodes": nodes, "links": links}
    except Exception as e:
        print(f"生成知识图谱时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成知识图谱时出错: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)