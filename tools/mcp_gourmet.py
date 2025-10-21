import os
import json
import asyncio
import httpx
import random
import uvicorn
from collections import OrderedDict
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query, Body
from fastmcp import FastMCP
from pydantic import BaseModel, RootModel, Field
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from typing import Optional, List, Dict, Annotated
# import sys # Disable when executing under root folder
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Disable when executing under root folder
# from utils.llm_client import GeminiClient, OllamaClient

class PlaceResponse(BaseModel):
    """
    Return Format of Get Gourmets List.
    """
    id: int
    name: str
    type: str
    specialty: str

class PlaceName(BaseModel):
    """
    Request Body of Query Menu, Delete Gourmet Shop or other functions which requiring only place_name for input.
    """
    place_name: str = Field(..., description="restaurant or drink shop name", example="McDonald's")

class MenuItem(RootModel[Dict[str, str]]):
    """
    Represents a single item in the menu.
    """
    # class Config:
    #     extra_forbid = True
    pass

class UpdateMenu(BaseModel):
    """
    Request Body of Update Menu of the Gourmet Shop.
    """
    place_name: str = Field(..., description="restaurant or drink shop name", example="McDonald's")
    updated_menu: List[MenuItem] = Field(..., 
                                         description="restaurant or drink shop manu in list of dicts format, where dict key represents dish name and dict value represents dish price.",
                                         example=[
                                             {"青菜蛋炒飯": "100"},
                                             {"叉燒蛋炒飯": "115"}
                                             ]
                                         )

class NewPlace(BaseModel):
    """
    Request Body of Create Gourmet Shop.
    """
    name: str = Field(..., description="restaurant or drink shop name", example="McDonald's")
    type: str = Field(..., description="type of gourmet shop, only 'food' or 'drink' are available. 'food' represents restaurants, 'drink' represents drink shops.", example="food")
    specialty: str = Field(..., description="specialty of the shop", example="fried chicken, cheese burger.")
    # menu: Optional[List[MenuItem]] = None
    menu: Optional[List[MenuItem]] = Field(None,  
        description="List of menu items from a restaurant or drink shop. If the menu parameter is not present in the request body, the menu parameter defaults to None.",
        example=[
            {"青菜蛋炒飯": "100"},
            {"叉燒蛋炒飯": "115"}
            ]
    )

class PlaceType(BaseModel):
    """
    Request Body of Randomly Picking a Gourmet Shop.
    """
    type: str = Field(..., description="type of gourmet shop, only 'food' or 'drink' are available. 'food' represents restaurants, 'drink' represents drink shops.", example="food")

load_dotenv(".env")
places_path = os.getenv("PLACES_PATH")
file_lock = asyncio.Lock()

app = FastAPI(title="Lunch&Drink API")
mcp = FastMCP()

# Declaring API Endpoints
@app.get("/")
def read_root():
    return {"message": "API Server running normally."}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@asynccontextmanager
async def locked_file_operation(mode: str = "r"):
    await file_lock.acquire()
    try:
        with open(places_path, mode, encoding="utf-8") as file:
            yield file
    finally:
        file_lock.release()

@app.get(
        "/get_places", 
        response_model=List[PlaceResponse], 
        summary="列出所有店家"
        )
async def get_places(
    type: Annotated[Optional[str], Query(
        description="optional params for filtering, only 'food' or 'drink' are available. 'food' represents restaurants, 'drink' represents drink shops.",
        example="food"
        )
    ] = None
):
    """
    列出所有登錄的餐廳或飲料店
    
    查詢參數說明：
    - **type**: 店家類型, 只能是 'food' (餐廳) 或 'drink' (飲料店), 這個參數是optional
    """
    with open(places_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    places = [PlaceResponse(**place) for place in data]
    if type:
        places = [place for place in places if place.type == type]
    return places


@app.post(
        "/query_menu", 
        summary="查詢店家菜單")
async def query_menu(
    payload: Annotated[PlaceName, Body(
        openapi_examples={
            "query_example": {
                "summary": "查詢菜單範例",
                "description": "查詢麥當勞菜單",
                "value": {"place_name": "McDonald's"}
                }
            }
        )
    ]
):
    """
    輸入店家名稱來查詢特定餐廳或飲料店的菜單
    
    參數說明：
    - **place_name**: 店家名稱（必填）
    """
    try:
        data = payload.model_dump()
        query_name = data.get("place_name")
        if not query_name:
            raise HTTPException(status_code=400, detail="place_name is required")
        with open(places_path, "r", encoding="utf-8") as file:
            places_data = json.load(file)
        for place in places_data:
            if place["name"] == query_name:
                return {"菜單": place["menu"]}
            else:
                continue
        return {"狀態": "您尋找的餐廳未被登錄"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

@app.post(
    "/create_place", 
    summary="新增美食店家")
async def create_place(
    new_place: Annotated[NewPlace, Body(
        openapi_examples={
            "restaurant": {
                "summary": "新增餐廳範例",
                "description": "新增一家炒飯店",
                "value": {
                    "name": "老王炒飯",
                    "type": "food",
                    "specialty": "蛋炒飯、叉燒炒飯",
                    "menu": [
                        {"青菜蛋炒飯": "100"},
                        {"叉燒蛋炒飯": "115"}
                    ]
                }
            },
            "drink_shop": {
                "summary": "新增飲料店範例",
                "description": "新增一家手搖飲店",
                "value": {
                    "name": "50嵐",
                    "type": "drink",
                    "specialty": "珍珠奶茶、波霸奶茶",
                    "menu": [
                        {"珍珠奶茶": "55"},
                        {"波霸奶茶": "60"}
                    ]
                }
            }
        }
    )]
):
    """
    新增一家新的餐廳或飲料店到資料庫
    
    參數說明：
    - **name**: 店家名稱 (必填)
    - **type**: 店家類型, 只能是 'food' (餐廳) 或 'drink' (飲料店)
    - **specialty**: 店家特色或招牌餐點
    - **menu**: 菜單列表(選填), 格式為List of dicts, key 為品項名稱, value 為價格
    """
    try:
        async with locked_file_operation("r") as file:
            places_data = json.load(file)
        # Check Repeat
        for place in places_data:
            if place["name"] == new_place.name:
                raise HTTPException(status_code=400, detail="Your place is repeated.")
        # Get Latest ID
        if places_data:
            last_id = places_data[-1]["id"]
        else:
            last_id = 0
        new_id = last_id + 1
        # Create New Place
        new_place_dict = new_place.model_dump()
        # Re-Order
        ordered_dict = OrderedDict()
        ordered_dict["id"] = new_id
        for key, value in new_place_dict.items():
            ordered_dict[key] = value
        # Insert New Place
        places_data.append(ordered_dict)
        async with locked_file_operation("w") as file:
            json.dump(places_data, file, indent=4, ensure_ascii=False)
        return {"message": "Place created successfully", "new_place": ordered_dict}
    except HTTPException as errmsg:
        raise errmsg
    except Exception as errmsg:
        raise HTTPException(status_code=500, detail=str(errmsg))

@app.put(
        "/update_menu", 
        summary="更新店家菜單")
async def update_menu(
    payload: Annotated[UpdateMenu, Body(
        openapi_examples={
            "update_example": {
                "summary": "更新店家菜單範例",
                "description":  "更新麥當勞菜單",
                "value": {
                    "place_name": "McDonald's",
                    "updated_menu": [
                        {"Big Mac": "85"},
                        {"McNuggets 6pcs": "70"},
                        {"French Fries": "45"}
                        ]
                    }
                }
            }
        )
    ]
):
    """
    更新指定餐廳或飲料店的菜單內容。可以完全替換原有菜單。

    請注意：
    - 此操作會完全替換原有菜單
    - updated_menu 為新的完整菜單列表

    參數說明：
    - **place_name**: 店家名稱 (必填)
    - **updated_menu**: 新菜單列表(必填), 格式為List of dicts, key 為品項名稱, value 為價格
    """
    try:
        data = payload.model_dump()
        place_name = data.get("place_name")
        updated_menu = data.get("updated_menu")
        if not place_name:
            raise HTTPException(status_code=400, detail="place_name is required")
        if updated_menu is None:
            raise HTTPException(status_code=400, detail="updated_menu is required")

        async with locked_file_operation("r") as file:
            places_data = json.load(file)

        found = False
        for place in places_data:
            if place["name"] == place_name:
                place["menu"] = updated_menu
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="Place not found")

        async with locked_file_operation("w") as file:
            json.dump(places_data, file, indent=4, ensure_ascii=False)
        return {"message": "Menu updated successfully"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.delete(
        "/delete_place", 
        summary="刪除店家")
async def delete_place(
    payload: Annotated[PlaceName, Body(
        openapi_examples={
            "delete_example": {
                "summary": "刪除店家範例",
                "description": "刪除麥當勞",
                "value": {"place_name": "McDonald's"}
            }
        }
    )]
):
    """
    刪除特定餐廳或飲料店
    
    此端點用於從資料庫中永久刪除指定的餐廳或飲料店。
    刪除後將無法復原，請謹慎使用。
    
    參數說明：
    - **place_name**: 要刪除的餐廳或飲料店名稱 (必填)
    """
    try:
        data = payload.model_dump()
        place_name = data.get("place_name")
        if not place_name:
            raise HTTPException(status_code=400, detail="place_name is required")
        
        async with locked_file_operation("r") as file:
            places_data = json.load(file)

        found = False
        for _, place in enumerate(places_data):
            if place["name"] == place_name:
                del places_data[_]
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="Place not found")

        async with locked_file_operation("w") as file:
            json.dump(places_data, file, indent=4, ensure_ascii=False)
        return {"message": "Place deleted successfully"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@app.post(
    "/random_place", 
    summary="店家抽抽看")
async def random_place(
    payload: Annotated[PlaceType, Body(
        openapi_examples={
            "food_example": {
                "summary": "隨機選擇餐廳",
                "description": "從所有餐廳中隨機選擇一家",
                "value": {"type": "food"}
            },
            "drink_example": {
                "summary": "隨機選擇飲料店",
                "description": "從所有飲料店中隨機選擇一家",
                "value": {"type": "drink"}
            }
        }
    )]
):
    """
    隨機決定一家餐廳或飲料店
    
    此端點用於幫助使用者從指定類型的店家中隨機選擇一家。
    適合用於選擇困難時的決策輔助。
    
    參數說明：
    - **type**: 店家類型 (必填)
      - 'food': 從餐廳中隨機選擇
      - 'drink': 從飲料店中隨機選擇
    """
    try:
        data = payload.model_dump()
        place_type = data.get("type")
        if not place_type:
            raise HTTPException(status_code=400, detail="type is required")
        
        async with locked_file_operation("r") as file:
            places_data = json.load(file)

        filtered_places = [place for place in places_data if place["type"] == place_type]
        if not filtered_places:
            raise HTTPException(status_code=404, detail="No places found with the specified type")

        random_place = random.choice(filtered_places)
        return {"random_place": random_place}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

# Defining MCP Tools
@mcp.tool(
        title="美食選擇器",
        name="mcp_draw_gourmet", # Please note that this will override the function name.
        description="Help users randomly selecting a food shop or drink shop. Ask first if they want food or drink. Call mcp_draw_gourmet with a JSON body, e.g. {\"payload\": {\"type\":\"food\"}}. Only food and drink are valid.",
        tags={"catalog", "randomizer"})
async def mcp_draw_gourmet(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://10.13.60.113:8081/random_place", json=data)
        if response.status_code == 200:
            return f"response_text: {response.json()}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to Draw Shop."}  
    
@mcp.tool(
        title="美食店家清單",
        name="mcp_get_gourmet_list", # Please note that this will override the function name.
        description="Help users to get restaurant list or drink shop list. To Call mcp_get_gourmet_list, you need to input a single string from food or drink, any other strings are invalid input which will cause error.",
        tags={"catalog", "retriever"})
async def mcp_get_gourmet_list(payload: str = None):
    if payload:
        if "food" in payload:
            place_url = f"http://10.13.60.113:8081/get_places?type=food"
        elif "drink" in payload:
            place_url = f"http://10.13.60.113:8081/get_places?type=drink"
        else:
            place_url = "http://10.13.60.113:8081/get_places"
    else:
        place_url = "http://10.13.60.113:8081/get_places"
    async with httpx.AsyncClient() as client:
        response = await client.get(place_url)
        if response.status_code == 200:  
            return f"response_text: {response.json()}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to retrieve shop list."}  

@mcp.tool(
        title="查詢餐廳菜單",
        name="mcp_query_menu", # Please note that this will override the function name.
        description="Help users to get the menu of queried restaurant or drink shop. Call mcp_query_menu with a JSON string, e.g. {\"payload\": {\"place_name\":\"McDonalds\"}} to get the menu, please note that the value of place_name is shop name from user.",
        tags={"catalog", "retriever"})
async def mcp_query_menu(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://10.13.60.113:8081/query_menu", json=data)
        if response.status_code == 200:  
            return f"response_text: {response.json()}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to query menu."}  

@mcp.tool(
        title="新增餐廳",
        name="mcp_add_gourmet_shop", # Please note that this will override the function name.
        description="Help users to add gourmet shop to the database. Call mcp_add_gourmet_shop with a JSON string, e.g. {\"name\": \"McDonald's\",\"type\": \"food\",\"specialty\":\"Hamburger, Fried Chicken, Fries, McNuggets\",\"menu\": [{\"Big Mac\": \"81\"},{\"McNuggets 6pcs\": \"69\"}]}.",
        tags={"catalog", "creator"})
async def mcp_add_gourmet_shop(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://10.13.60.113:8081/create_place", json=data)
        if response.status_code == 200:  
            return f"response_text: {response.json()}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to add shop."}  

@mcp.tool(
        title="更新餐廳菜單",
        name="mcp_update_menu", # Please note that this will override the function name.
        description="Help users to update the menu of a gourmet shop. Call mcp_update_menu with a JSON string, e.g. {\"place_name\": \"MacDonalds\",\"updated_menu\":[{\"BigMac\": \"81\"},{\"McNuggets 6pcs\": \"69\"}]}.",
        tags={"catalog", "updater"})
async def mcp_update_menu(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="PUT",
            url="http://10.13.60.113:8081/update_menu",
            json=data
        )
        if response.status_code == 200:  
            return f"response_text: {response.json()}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to update menu."}  

@mcp.tool(
        title="刪除餐廳",
        name="mcp_delete_gourmet_shop", # Please note that this will override the function name.
        description="Help users to delete a gourmet shop from database. Call mcp_delete_gourmet_shop with a JSON string, e.g. {\"payload\": {\"place_name\":\"McDonalds\"}}.",
        tags={"catalog", "deleter"})
async def mcp_delete_gourmet_shop(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="DELETE",
            url="http://10.13.60.113:8081/delete_place",
            json=data
        )
        if response.status_code == 200:  
            return f"response_text: {response}"
        else:  
            print(f"Error: Received status code {response.status_code}")  
        return {"error": "Failed to delete shop."}  

# MCP 測試用

@mcp.tool(
        title="查詢向量資料庫KBTEST01",
        name="kbtest_001", # Please note that this will override the function name.
        description="Query Vector Store KBTEST01, the store contains all the data from creditcard department.",
        tags={"catalog", "retriever"})
async def mcp_retrieve_kbtest01():
    response = {
        "text_id": "kbtest_001",
        "text": "您所查詢的信用卡發卡案件編號是TEST20250901。"
    }
    return f"response_text: {response}"

@mcp.tool(
        title="查詢向量資料庫KBTEST02",
        name="kbtest_002", # Please note that this will override the function name.
        description="Query Vector Store KBTEST02, the store contains all the data from corporate banking department.",
        tags={"catalog", "retriever"})
async def mcp_retrieve_kbtest02():
    response = {
        "text_id": "kbtest_002",
        "text": "您查詢的貸款案件TEST20250901目前的狀態是正在審核客戶資料中。"
    }
    return f"response_text: {response}"

@mcp.tool(
        title="查詢向量資料庫KBTEST03",
        name="kbtest_003", # Please note that this will override the function name.
        description="Query Vector Store KBTEST03, the store contains all the data from audit department.",
        tags={"catalog", "retriever"})
async def mcp_retrieve_kbtest03():
    response = {
        "text_id": "kbtest_003",
        "text": "您查詢的待審案件TEST20250901已審核通過。"
    }
    return f"response_text: {response}"

# Mounting MCP to FastAPI
mcp_app = mcp.http_app(transport="streamable-http")
routes = [
    *mcp_app.routes,
    *app.routes
]
mcp_gourmet = FastAPI(
    routes=routes,
    lifespan=mcp_app.lifespan,
)

mcp_gourmet.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

if __name__ == "__main__":
    uvicorn.run(mcp_gourmet, host="0.0.0.0", port=8081)