from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import litellm
from fastmcp import FastMCP
from milvus_client import MilvusManager

# 初始化 Milvus 客戶端
# 實際應用中，這些參數可以從環境變數或設定檔中讀取
MILVUS_CLIENT = MilvusManager(host='localhost', port=19530)
COLLECTION_NAME = "your_collection_name" # 請替換為你的 collection 名稱

# LiteLLM 相關設定
LITELLM_API_BASE = "http://your-litellm-api-base-url" # 替換為你的 LiteLLM API 位址
LITELLM_MODEL = "qwen-embedding" # 替換為你的 qwen embedding 模型名稱

class SearchRequest(BaseModel):
    query: str = Field(..., description="User's text query for vector search.")
    top_k: int = Field(10, gt=0, description="The number of most similar results to return.")

class SearchResponse(BaseModel):
    results: list = Field(..., description="List of search results.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initial Event Check when startup app.
    """
    try:
        if not MILVUS_CLIENT.client.has_collection(collection_name=COLLECTION_NAME):
            raise ValueError(f"Collection '{COLLECTION_NAME}' does not exist. Please create it first.")
        print(f"Successfully connected to Milvus and found collection '{COLLECTION_NAME}'.")
    except Exception as e:
        print(f"Failed to connect to Milvus or find collection: {e}")
        raise RuntimeError("Failed to start application due to Milvus connection error.")
    
app = FastAPI(
    title="Milvus Vector Search API",
    description="An API for performing vector similarity search on Milvus.",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):

    try:
        # 1. 使用 LiteLLM 獲取使用者查詢的 embedding
        response = await litellm.get_embedding_async(
            model=LITELLM_MODEL,
            input=[request.query],
            api_base=LITELLM_API_BASE
        )
        
        if not response or not response.data:
            raise HTTPException(status_code=500, detail="Failed to get embedding from LiteLLM.")
        
        query_vector = [item.embedding for item in response.data]

        # 2. 在 Milvus 中進行向量搜尋
        search_results = MILVUS_CLIENT.search_vectors(
            collection_name=COLLECTION_NAME,
            query_vectors=query_vector,
            top_k=request.top_k
        )
        
        if search_results is None:
            raise HTTPException(status_code=500, detail="Milvus search failed.")
            
        # 3. 處理並回傳結果
        formatted_results = []
        for hit in search_results[0]:
            formatted_results.append({
                "id": hit['id'],
                "distance": hit['distance']
            })
            
        return {"results": formatted_results}

    except litellm.APIError as e:
        raise HTTPException(status_code=e.status_code, detail=f"LiteLLM API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

mcp = FastMCP.from_fastapi(app=app)

if __name__ == '__main__':
    mcp.run()