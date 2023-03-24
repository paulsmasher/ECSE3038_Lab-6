from fastapi import FastAPI, Request, HTTPException
import os
import motor.motor_asyncio
import pydantic
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from geopy.geocoders import Nominatim
import datetime
import pytz
import requests
import datetime
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

origins = [
    "https://rg-lab6-api.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_BD_URL"))
db = client.lab_6
states = db["state"]

pydantic.json.ENCODERS_BY_TYPE[ObjectId]=str

geolocator = Nominatim(user_agent="MyApp")
location = geolocator.geocode("Hyderabad")
user_latitude = location.latitude
user_longitude = location.longitude

sunset_api_endpoint = f'https://ecse-sunset-api.onrender.com/api/sunset'
sunset_api_response = requests.get(sunset_api_endpoint)
sunset_api_data = sunset_api_response.json()
sunset_time = datetime.datetime.strptime(sunset_api_data['sunset'], '%Y-%m-%dT%H:%M:%S.%f').time()

@app.put("/api/temperature")
async def toggle(request: Request):
    state = await request.json()
    state["light"] = (sunset_time < get_current_time())
    state["fan"] = (float(state["temperature"]) >= 28.0)

    obj = await states.find_one({"tobe":"updated"})
    if obj:
        await states.update_one({"tobe":"updated"}, {"$set": state})
    else:
        await states.insert_one({**state, "tobe": "updated"})
    new_obj = await states.find_one({"tobe":"updated"})
    return new_obj, 204

@app.get("/api/state")
async def get_state():
    state = await states.find_one({"tobe": "updated"})
    if state is None:
        return {"fan": False, "light": False}

    state["fan"] = (float(state["temperature"]) >= 28.0)
    state["light"] = (sunset_time < get_current_time())

    await states.update_one({"_id": state["_id"]}, {"$set": {"fan": state["fan"], "light": state["light"]}})

    return state

def get_current_time():
    geolocator = Nominatim(user_agent="MyApp")
    location = geolocator.reverse(f"{user_latitude}, {user_longitude}")
    timezone_str = location.raw["timezone"]
    timezone = pytz.timezone(timezone_str)
    current_time = datetime.datetime.now(timezone).time()
    return current_time