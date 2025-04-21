from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import uuid
from processor import DocumentProcessor
import json

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)