import os
import json
import asyncio
import httpx
import random
import uvicorn
from collections import OrderedDict
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastmcp import FastMCP
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from typing import Optional, List
import sys # Disable when executing under root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Disable when executing under root folder
from utils.llm_client import GeminiClient, OllamaClient

class PlaceResponse(BaseModel):
    id: int
    name: str
    type: str
    specialty: str

class PlaceName(BaseModel):
    place_name: str

class NewPlace(BaseModel):
    name: str
    type: str
    specialty: str
    menu: Optional[List[dict]] = None

class UpdateMenu(BaseModel):
    place_name: str
    updated_menu: List[dict]

class PlaceType(BaseModel):
    type: str

class TestRequest(BaseModel):
    request: str

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

@app.get("/get_places", response_model=List[PlaceResponse])
async def get_places(type: Optional[str] = None):
    with open(places_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    places = [PlaceResponse(**place) for place in data]
    if type:
        places = [place for place in places if place.type == type]
    return places

@app.post("/query_menu")
async def query_menu(payload: PlaceName):
    try:
        data = payload.model_dump()
        query_name = data.get("place_name")
        if not query_name:
            raise HTTPException(status_code=400, detail="place_name is required")
        with open(places_path, "r", encoding="utf-8") as file:
            places_data = json.load(file)
        for place in places_data:
            if place.get("name") == query_name:
                return {"菜單": place.get("menu")}
            else:
                return {"狀態": "您尋找的餐廳未被登錄"}
        raise HTTPException(status_code=404, detail="Retrieving Menu Error.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

@app.post("/create_place")
async def create_place(new_place: NewPlace):
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

@app.put("/update_menu")
async def update_menu(payload: UpdateMenu):
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

@app.delete("/delete_place")
async def delete_place(payload: PlaceName):
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

@app.post("/random_place")
async def random_place(payload: PlaceType):
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
        description="Help users randomly selecting a food shop or drink shop. Ask first if they want food or drink. Call mcp_draw_gourmet with a JSON body, e.g. {\"type\":\"food\"}. Only food and drink are valid.",
        tags={"catalog", "randomizer"},
        meta={"version": "1.1", "author": "Shaun"})
async def mcp_draw_gourmet(payload: str):
    try:
        data = json.loads(payload)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://127.0.0.1:8081/random_place", json=data)
        return response.json()
    
@mcp.tool(
        title="美食店家清單",
        name="mcp_get_gourmet_list", # Please note that this will override the function name.
        description="Help users to get restaurant list or drink shop list.",
        tags={"catalog", "retriever"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_get_gourmet_list(type: str = None):
    if type:
        if type == "food" or "drink":
            place_url = f"http://127.0.0.1:8081/get_places?type={type}"
        else:
            place_url = "http://127.0.0.1:8081/get_places"
    else:
        place_url = "http://127.0.0.1:8081/get_places"
    async with httpx.AsyncClient() as client:
        response = await client.get(place_url)
        return response.json()

@mcp.tool(
        title="查詢餐廳菜單",
        name="mcp_query_menu", # Please note that this will override the function name.
        description="Help users to get the menu of queried restaurant or drink shop. Call mcp_query_menu with a JSON string, e.g. {\"place_name\":\"McDonald's\"}.",
        tags={"catalog", "retriever"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_query_menu(place_name: str):
    try:
        data = json.loads(place_name)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://127.0.0.1:8081/query_menu", json=data)
        return response.json()

@mcp.tool(
        title="新增餐廳",
        name="mcp_add_gourmet_shop", # Please note that this will override the function name.
        description="Help users to add gourmet shop to the database. Call mcp_add_gourmet_shop with a JSON string, e.g. {\"name\": \"McDonald's\",\"type\": \"food\",\"specialty\":\"Hamburger, Fried Chicken, Fries, McNuggets\",\"menu\": [{\"Big Mac\": \"81\"},{\"McNuggets 6pcs\": \"69\"}]}.",
        tags={"catalog", "creator"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_add_gourmet_shop(shop_info: str):
    try:
        data = json.loads(shop_info)
    except Exception as err:
      raise HTTPException(status_code=400, detail=str(err))
    async with httpx.AsyncClient() as client:
        response = await client.post("http://127.0.0.1:8081/create_place", json=data)
        return response.json()

#待做
# @mcp.tool(
#         title="更新餐廳菜單",
#         name="mcp_update_menu", # Please note that this will override the function name.
#         description="XXX. Call mcp_update_menu with a JSON string, e.g. {\"place_name\":\"McDonald's\"}.",
#         tags={"catalog", "updater"},
#         meta={"version": "1.0", "author": "Shaun"})
# async def mcp_update_menu(new_menu: str):
#     pass

# @mcp.tool(
#         title="刪除餐廳",
#         name="mcp_delete_gourmet_shop", # Please note that this will override the function name.
#         description="XXX. Call mcp_delete_gourmet_shop with a JSON string, e.g. {\"place_name\":\"McDonald's\"}.",
#         tags={"catalog", "deleter"},
#         meta={"version": "1.0", "author": "Shaun"})
# async def mcp_delete_gourmet_shop(place_name: str):
#     pass

# MCP 測試用

@mcp.tool(
        title="查詢向量資料庫KBTEST01",
        name="kbtest_001", # Please note that this will override the function name.
        description="查詢向量資料庫KBTEST01",
        tags={"catalog", "retriever"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_retrieve_kbtest01():
    response = {
        "state": "succeed",
        "content": "kbtest_001"
    }
    return response

@mcp.tool(
        title="查詢向量資料庫KBTEST02",
        name="kbtest_002", # Please note that this will override the function name.
        description="查詢向量資料庫KBTEST02",
        tags={"catalog", "retriever"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_retrieve_kbtest02():
    response = {
        "state": "succeed",
        "content": "kbtest_002"
    }
    return response

@mcp.tool(
        title="查詢向量資料庫KBTEST03",
        name="kbtest_002", # Please note that this will override the function name.
        description="查詢向量資料庫KBTEST03",
        tags={"catalog", "retriever"},
        meta={"version": "1.0", "author": "Shaun"})
async def mcp_retrieve_kbtest03():
    response = {
        "state": "succeed",
        "content": "kbtest_003"
    }
    return response

# Mounting MCP to FastAPI
mcp_app = mcp.http_app(transport="streamable-http")
routes = [
    *mcp_app.routes,
    *app.routes
]
jasonapp = FastAPI(
    routes=routes,
    lifespan=mcp_app.lifespan,
)

jasonapp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

if __name__ == "__main__":
    uvicorn.run(jasonapp, host="127.0.0.1", port=8081)