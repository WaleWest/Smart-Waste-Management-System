from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import threading
import os

app = FastAPI()
data_file = "bin_data.json"
file_lock = threading.Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WasteBin(BaseModel):
    id: Optional[int] = None
    location: str
    fillLevel: Optional[int] = 0
    needsCollection: Optional[bool] = False
    lastUpdated: Optional[str] = None

def current_timestamp():
    return datetime.utcnow().isoformat(timespec='milliseconds') + "Z"

def load_bins():
    with file_lock:
        if not os.path.exists(data_file):
            return []
        with open(data_file, "r") as f:
            return json.load(f)

def save_bins(bins):
    with file_lock:
        with open(data_file, "w") as f:
            json.dump(bins, f, indent=4)

def get_next_bin_id(bins):
    if not bins:
        return 1
    return max(bin["id"] for bin in bins) + 1

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><head><title>Smart Waste Management API</title></head>
    <body>
        <h1>Smart Waste Management System API (User Version)</h1>
        <ul>
            <li>GET /bins - List all bins</li>
            <li>POST /bins - Add a bin</li>
            <li>GET /bins/{id} - Get bin by ID</li>
            <li>PUT /bins/{id} - Update bin by ID</li>
            <li>DELETE /bins/{id} - Delete bin by ID</li>
        </ul>
    </body></html>
    """

@app.post("/bins", status_code=201)
def add_bin(bin: WasteBin):
    bins = load_bins()
    bin.id = get_next_bin_id(bins)
    bin.lastUpdated = current_timestamp()
    bins.append(bin.dict())
    save_bins(bins)
    return {"success": True, "message": "Bin added successfully", "data": bin}

@app.get("/bins", response_model=List[WasteBin])
def get_all_bins():
    return load_bins()

@app.get("/bins/{bin_id}", response_model=WasteBin)
def get_bin(bin_id: int):
    bins = load_bins()
    for bin in bins:
        if bin["id"] == bin_id:
            return bin
    raise HTTPException(status_code=404, detail="Bin not found")

@app.put("/bins/{bin_id}")
def update_bin(bin_id: int, update: WasteBin):
    bins = load_bins()
    for idx, bin in enumerate(bins):
        if bin["id"] == bin_id:
            if update.location:
                bin["location"] = update.location
            if update.fillLevel is not None:
                bin["fillLevel"] = min(max(update.fillLevel, 0), 100)
            if update.needsCollection is not None:
                bin["needsCollection"] = update.needsCollection
            bin["lastUpdated"] = current_timestamp()
            bins[idx] = bin
            save_bins(bins)
            return {"success": True, "message": "Bin updated", "data": bin}
    raise HTTPException(status_code=404, detail="Bin not found")

@app.delete("/bins/{bin_id}")
def delete_bin(bin_id: int):
    bins = load_bins()
    new_bins = [bin for bin in bins if bin["id"] != bin_id]
    if len(new_bins) == len(bins):
        raise HTTPException(status_code=404, detail="Bin not found")
    save_bins(new_bins)
    return {"success": True, "message": "Bin deleted"}

