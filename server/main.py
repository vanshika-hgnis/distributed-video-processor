import os
import uuid
import json
import aiofiles
import uvicorn
from typing import Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pika
import asyncio
from datetime import datetime

app = FastAPI(title="Video Processing Pipeline")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory if it doesn't exist
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Store file processing status
# Status: "unprocessed", "enhancement_processed", "metadata_processed", "both_processed"
file_status: Dict[str, Dict] = {}

# Configure RabbitMQ connection
def get_rabbitmq_connection():
    return pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        # Send client ID to the client
        await websocket.send_text(json.dumps({"type": "connection", "client_id": client_id}))
        
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        if client_id in active_connections:
            del active_connections[client_id]

# Video upload endpoint
@app.post("/upload")
async def upload_video(file: UploadFile = File(...), client_id: str = None):
    if not client_id or client_id not in active_connections:
        raise HTTPException(status_code=400, detail="Invalid client ID")
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    file_extension = original_filename.split('.')[-1]
    filename = f"{file_id}.{file_extension}"
    file_path = os.path.join(STORAGE_DIR, filename)
    
    # Save the uploaded file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Store file status
    file_status[file_id] = {
        "status": "unprocessed",
        "client_id": client_id,
        "original_filename": original_filename,
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "enhancement_done": False,
        "metadata_done": False,
        "metadata": None,
        "enhanced_file_path": None
    }
    
    # Publish task to RabbitMQ
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Declare a fanout exchange
        channel.exchange_declare(exchange='video_processing', exchange_type='fanout')
        
        # Publish message
        message = json.dumps({
            "file_id": file_id,
            "file_path": file_path,
            "client_id": client_id
        })
        channel.basic_publish(
            exchange='video_processing',
            routing_key='',  # In fanout exchange, routing key is ignored
            body=message
        )
        
        connection.close()
        
        # Notify client that upload was successful
        await active_connections[client_id].send_text(json.dumps({
            "type": "upload_success",
            "file_id": file_id,
            "message": "Video uploaded successfully and processing started"
        }))
        
        return {"file_id": file_id, "message": "Video uploaded successfully and processing started"}
    
    except Exception as e:
        # Clean up the file in case of error
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error publishing task: {str(e)}")

# Internal endpoint for video enhancement status updates
@app.post("/internal/video-enhancement-status")
async def video_enhancement_status(data: dict):
    file_id = data.get("file_id")
    if not file_id or file_id not in file_status:
        raise HTTPException(status_code=400, detail="Invalid file ID")
    
    # Update file status
    file_status[file_id]["enhancement_done"] = True
    file_status[file_id]["enhanced_file_path"] = data.get("enhanced_file_path")
    
    # Check if both processes are complete
    if file_status[file_id]["enhancement_done"] and file_status[file_id]["metadata_done"]:
        file_status[file_id]["status"] = "both_processed"
        
        # Get client WebSocket
        client_id = file_status[file_id]["client_id"]
        if client_id in active_connections:
            # Send complete data to client
            await active_connections[client_id].send_text(json.dumps({
                "type": "processing_complete",
                "file_id": file_id,
                "metadata": file_status[file_id]["metadata"],
                "enhanced_video_path": file_status[file_id]["enhanced_file_path"]
            }))
    else:
        file_status[file_id]["status"] = "enhancement_processed"
    
    return {"status": "success"}

# Internal endpoint for metadata extraction status updates
@app.post("/internal/metadata-extraction-status")
async def metadata_extraction_status(data: dict):
    file_id = data.get("file_id")
    if not file_id or file_id not in file_status:
        raise HTTPException(status_code=400, detail="Invalid file ID")
    
    # Update file status
    file_status[file_id]["metadata_done"] = True
    file_status[file_id]["metadata"] = data.get("metadata")
    
    # Check if both processes are complete
    if file_status[file_id]["enhancement_done"] and file_status[file_id]["metadata_done"]:
        file_status[file_id]["status"] = "both_processed"
        
        # Get client WebSocket
        client_id = file_status[file_id]["client_id"]
        if client_id in active_connections:
            # Send complete data to client
            await active_connections[client_id].send_text(json.dumps({
                "type": "processing_complete",
                "file_id": file_id,
                "metadata": file_status[file_id]["metadata"],
                "enhanced_video_path": file_status[file_id]["enhanced_file_path"]
            }))
    else:
        file_status[file_id]["status"] = "metadata_processed"
    
    return {"status": "success"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)