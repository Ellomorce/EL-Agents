import os
import json
import asyncio
import random
import uvicorn
from collections import OrderedDict
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastmcp import FastMCP
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from typing import Optional, List

class PlaceResponse(BaseModel):
    id: int
    name: str
    type: str
    specialty: str

class NewPlace(BaseModel):
    name: str
    type: str
    specialty: str
    menu: Optional[List[dict]] = None

load_dotenv(".env")
places_path = os.getenv("PLACES_PATH")
file_lock = asyncio.Lock()


# mcp = FastMCP("Jason")
# mcp_app = mcp.http_app(path='/mcp')
# app = FastAPI(title="Lunch&Drink API", lifespan=mcp_app.lifespan)
app = FastAPI(title="Lunch&Drink API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# app.mount("/yourjason", mcp_app)

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

@app.get("/places/get_places", response_model=List[PlaceResponse])
async def get_places(type: Optional[str] = None):
    with open(places_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    places = [PlaceResponse(**place) for place in data]
    if type:
        places = [place for place in places if place.type == type]
    return places

@app.post("/places/query_menu")
async def query_menu(request: Request):
    try:
        data = await request.json()
        name = data.get("place_name")
        if not name:
            raise HTTPException(status_code=400, detail="place_name is required")
        with open(places_path, "r", encoding="utf-8") as file:
            places_data = json.load(file)
        for place in places_data:
            if place.get("name") == name:
                return {"菜單": place.get("menu")}
        raise HTTPException(status_code=404, detail="Place not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

@app.post("/places/create_place")
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

@app.put("/places/update_menu")
async def update_menu(request: Request):
   try:
       data = await request.json()
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
   
@app.delete("/places/delete_place")
async def delete_place(request: Request):
   try:
       data = await request.json()
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

@app.post("/places/random_place")
async def random_place(request: Request):
  try:
      data = await request.json()
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)