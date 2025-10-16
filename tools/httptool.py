# 用於執行各種HTTP Methods
import json
import requests
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class HttpPostPayload(BaseModel):
    title: str = Field(..., description="要建立或更新的資源標題。")
    content: str = Field(..., description="要建立或更新的資源內容。")
    tags: Optional[List[str]] = Field(None, description="可選的標籤列表。")
    published: bool = Field(True, description="資源是否公開發佈。")

mcp = FastMCP(name="HTTP Proxy Server", instructions="此伺服器提供四種 HTTP 方法，以代理 LLM 對外部 API 進行調用。")

@mcp.tool
def get_openapi_schema(url: str):
    """
    對一個未知內容的API端點執行HTTP GET 請求，並回傳該API端點的Openapi Schema，以便後續生成訪問端點的請求指令。
    """
    if url.endswith('/'):
        base = url + "openapi.json"
    else:
        base = url + "/openapi.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return response.text
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP GET request failed: {e}"}

@mcp.tool
def http_post(url: str, data: HttpPostPayload) -> Dict[str, Any]:
    """
    使用結構化資料執行一個 HTTP POST 請求。用於在遠端伺服器上創建新資源。
    Args:
        url (str): 目標 API 網址。
        data (HttpPostPayload): 包含 JSON 請求主體的結構化資料。
    Returns:
        Dict[str, Any]: 伺服器響應的 JSON 物件。
    """
    try:
        response = requests.post(url, json=data.model_dump())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP POST request failed: {e}"}

@mcp.tool
def http_put(url: str, data: HttpPostPayload) -> Dict[str, Any]:
    """
    使用結構化資料執行一個 HTTP PUT 請求。用於在遠端伺服器上更新現有資源。
    Args:
        url (str): 目標 API 網址。
        data (HttpPostPayload): 包含 JSON 請求主體的結構化資料。

    Returns:
        Dict[str, Any]: 伺服器響應的 JSON 物件。
    """
    try:
        response = requests.put(url, json=data.model_dump())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP PUT request failed: {e}"}

@mcp.tool
def http_delete(url: str) -> Dict[str, Any]:
    """
    執行一個 HTTP DELETE 請求，用於刪除遠端伺服器上的資源。
    Args:
        url (str): 目標 API 網址。
    Returns:
        Dict[str, Any]: 伺服器響應的 JSON 物件。
    """
    try:
        response = requests.delete(url)
        response.raise_for_status()
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"status": "success", "message": "Resource deleted successfully."}
    except requests.exceptions.RequestException as e:
        return {"error": f"HTTP DELETE request failed: {e}"}

@mcp.tool()
def structured_data_converting(generated_content):
    """
    Converts a natural language prompt into a structured JSON object based on a provided API schema.
    """
    try:
        structured_data = json.loads(generated_content)
        return structured_data

    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        return {"error": str(e), "message": "Failed to generate valid structured output."}

if __name__ == "__main__":
    print("Starting FastMCP server with HTTP transport on port 8000...")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
    print("Server stopped.")