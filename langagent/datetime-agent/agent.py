from typing import TypedDict, Annotated, Optional, List
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_models import ChatLiteLLM
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json
import uvicorn

app = FastAPI(
    title="日期擷取 Agent API",
    description="從用戶查詢中提取日期時間資訊並轉換為指定格式",
    version="1.0.0"
)

class DateExtractionRequest(BaseModel):
    query: str = Field(..., description="用戶查詢文本")
    output_format: str = Field(
        default="iso8601",
        description="輸出格式: iso8601, timestamp, readable"
    )
    model_name: str = Field(
        default="hosted_vllm/gpt-oss-120b",
        description="LiteLLM Model"
    )

class DateInfo(BaseModel):
    original: str
    type: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    confidence: Optional[str] = None
    error: Optional[str] = None

class DateExtractionResponse(BaseModel):
    success: bool
    query: str
    extracted_dates: List[DateInfo]
    formatted_output: str
    error: Optional[str] = None

class DateExtractionState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    extracted_dates: Optional[list[dict]]
    output_format: str
    formatted_output: Optional[str]
    error: Optional[str]
    model_name: str

# 系統提示詞
SYSTEM_PROMPT = """你是一個專業的日期時間擷取助手。你的任務是從用戶的查詢中識別並提取所有日期和時間資訊。

請仔細分析用戶的輸入，識別以下類型的日期時間表達：
- 絕對日期：如「2024年3月15日」、「明天」、「下週一」
- 相對日期：如「三天後」、「上個月」、「去年」
- 時間點：如「下午3點」、「早上9:30」
- 日期範圍：如「這週」、「本月」、「2024年第一季」

當前日期時間參考點：{current_datetime}

請以 JSON 格式返回提取結果，格式如下：
{{
    "dates": [
        {{
            "original_text": "原始文字表達",
            "type": "absolute/relative/range",
            "start_datetime": "YYYY-MM-DDTHH:MM:SS",
            "end_datetime": "YYYY-MM-DDTHH:MM:SS (如果是範圍)",
            "confidence": "high/medium/low"
        }}
    ]
}}

如果沒有找到日期資訊，返回：{{"dates": []}}
"""

def extract_dates_node(state: DateExtractionState) -> DateExtractionState:
    """從用戶查詢中提取日期資訊"""
    user_query = state["user_query"]
    model_name = state.get("model_name", "hosted_vllm/gpt-oss-120b")
    current_datetime = datetime.now().isoformat()
    
    llm = ChatLiteLLM(model=model_name, temperature=0, )
    
    system_msg = SystemMessage(content=SYSTEM_PROMPT.format(
        current_datetime=current_datetime
    ))
    user_msg = HumanMessage(content=f"請從以下查詢中提取日期時間資訊：\n\n{user_query}")
    
    try:
        response = llm.invoke([system_msg, user_msg])
        content = response.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()
        
        result = json.loads(json_str)
        
        return {
            **state,
            "extracted_dates": result.get("dates", []),
            "messages": [response]
        }
    except Exception as e:
        return {
            **state,
            "error": f"日期提取失敗: {str(e)}",
            "extracted_dates": []
        }

def format_dates_node(state: DateExtractionState) -> DateExtractionState:
    """將提取的日期轉換為指定格式"""
    extracted_dates = state.get("extracted_dates", [])
    output_format = state.get("output_format", "iso8601")
    
    if not extracted_dates:
        return {
            **state,
            "formatted_output": "未找到日期資訊"
        }
    
    formatted_results = []
    
    for date_info in extracted_dates:
        try:
            formatted_date = {
                "original": date_info.get("original_text"),
                "type": date_info.get("type"),
            }
            
            if output_format == "iso8601":
                formatted_date["start"] = date_info.get("start_datetime")
                if date_info.get("end_datetime"):
                    formatted_date["end"] = date_info.get("end_datetime")
            
            elif output_format == "timestamp":
                start_dt = datetime.fromisoformat(date_info.get("start_datetime"))
                formatted_date["start"] = int(start_dt.timestamp())
                if date_info.get("end_datetime"):
                    end_dt = datetime.fromisoformat(date_info.get("end_datetime"))
                    formatted_date["end"] = int(end_dt.timestamp())
            
            elif output_format == "readable":
                start_dt = datetime.fromisoformat(date_info.get("start_datetime"))
                formatted_date["start"] = start_dt.strftime("%Y年%m月%d日 %H:%M:%S")
                if date_info.get("end_datetime"):
                    end_dt = datetime.fromisoformat(date_info.get("end_datetime"))
                    formatted_date["end"] = end_dt.strftime("%Y年%m月%d日 %H:%M:%S")
            
            formatted_date["confidence"] = date_info.get("confidence")
            formatted_results.append(formatted_date)
            
        except Exception as e:
            formatted_results.append({
                "original": date_info.get("original_text"),
                "error": f"格式轉換失敗: {str(e)}"
            })
    
    return {
        **state,
        "formatted_output": json.dumps(formatted_results, ensure_ascii=False, indent=2)
    }

def should_continue(state: DateExtractionState) -> str:
    """決定是否繼續處理"""
    if state.get("error"):
        return "end"
    return "format"

# 構建 LangGraph
def create_date_extraction_agent():
    """創建日期擷取 Agent 圖"""
    workflow = StateGraph(DateExtractionState)
    workflow.add_node("extract", extract_dates_node)
    workflow.add_node("format", format_dates_node)
    workflow.set_entry_point("extract")
    workflow.add_conditional_edges(
        "extract",
        should_continue,
        {
            "format": "format",
            "end": END
        }
    )
    workflow.add_edge("format", END)
    
    return workflow.compile()

agent = create_date_extraction_agent()

@app.get("/")
async def root():
    """存活探針"""
    return {
        "status": "running",
        "service": "日期擷取 Agent API",
        "version": "1.0.0"
    }

@app.post("/extract", response_model=DateExtractionResponse)
async def extract_dates(request: DateExtractionRequest):
    """
    從用戶查詢中提取日期時間資訊
    
    Args:
        request: 包含查詢文本和輸出格式的請求
    
    Returns:
        DateExtractionResponse: 提取的日期資訊
    """
    try:
        result = agent.invoke({
            "user_query": request.query,
            "output_format": request.output_format,
            "model_name": request.model_name,
            "messages": [],
            "extracted_dates": None,
            "formatted_output": None,
            "error": None
        })
        if result.get("error"):
            return DateExtractionResponse(
                success=False,
                query=request.query,
                extracted_dates=[],
                formatted_output="",
                error=result["error"]
            )
        try:
            formatted_data = json.loads(result["formatted_output"])
            date_infos = [DateInfo(**item) for item in formatted_data]
        except:
            date_infos = []
        
        return DateExtractionResponse(
            success=True,
            query=request.query,
            extracted_dates=date_infos,
            formatted_output=result["formatted_output"],
            error=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"處理請求時發生錯誤: {str(e)}")

@app.post("/extract/batch")
async def extract_dates_batch(queries: List[str], output_format: str = "iso8601"):
    """
    批量提取日期資訊
    
    Args:
        queries: 查詢文本列表
        output_format: 輸出格式
    
    Returns:
        批量處理結果
    """
    results = []
    for query in queries:
        try:
            result = agent.invoke({
                "user_query": query,
                "output_format": output_format,
                "model_name": "hosted_vllm/gpt-oss-120b",
                "messages": [],
                "extracted_dates": None,
                "formatted_output": None,
                "error": None
            })
            results.append({
                "query": query,
                "success": not bool(result.get("error")),
                "result": result["formatted_output"] if not result.get("error") else None,
                "error": result.get("error")
            })
        except Exception as e:
            results.append({
                "query": query,
                "success": False,
                "result": None,
                "error": str(e)
            })
    
    return {"results": results}

if __name__ == "__main__":
    uvicorn.run(
        "agent:app",
        host="0.0.0.0",
        port=4203,
        reload=True
    )