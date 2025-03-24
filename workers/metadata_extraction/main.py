import os
import cv2
import json
import pika
import time
import requests
from pathlib import Path
from datetime import datetime

# Configure RabbitMQ connection
import os
import pika

def get_rabbitmq_connection():
    connection_attempts = 0
    max_attempts = 10  # Increased retries
    while connection_attempts < max_attempts:
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv('RABBITMQ_HOST', 'rabbitmq'),  # Use Docker service name
                    port=5672,  # Default AMQP port
                    credentials=pika.PlainCredentials(
                        username=os.getenv('RABBITMQ_USER', 'guest'),
                        password=os.getenv('RABBITMQ_PASS', 'guest')
                    ),
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
        except pika.exceptions.AMQPConnectionError as e:
            connection_attempts += 1
            print(f"Failed to connect to RabbitMQ, attempt {connection_attempts}/{max_attempts}: {e}")
            time.sleep(10)  # Increased delay between retries
    raise Exception("Failed to connect to RabbitMQ after multiple attempts")

def extract_metadata(file_path):
    """Extract basic metadata from a video file"""
    try:
        # Get file info
        file_size = os.path.getsize(file_path)
        file_created = datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
        file_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        
        # Open the video file
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise Exception(f"Could not open video file: {file_path}")
        
        # Extract video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate duration in seconds
        duration = frame_count / fps if fps > 0 else 0
        
        # Format duration as mm:ss
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_formatted = f"{minutes:02d}:{seconds:02d}"
        
        # Extract codec information
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc = chr(fourcc_int & 0xFF) + chr((fourcc_int >> 8) & 0xFF) + chr((fourcc_int >> 16) & 0xFF) + chr((fourcc_int >> 24) & 0xFF)
        
        # Release resources
        cap.release()
        
        # Compile metadata
        metadata = {
            "file_name": os.path.basename(file_path),
            "file_size": file_size,
            "file_size_formatted": f"{file_size / (1024 * 1024):.2f} MB",
            "file_created": file_created,
            "file_modified": file_modified,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "fps": round(fps, 2),
            "frame_count": frame_count,
            "duration_seconds": duration,
            "duration": duration_formatted,
            "codec": fourcc,
            "extracted_at": datetime.now().isoformat()
        }
        
        print(f"Metadata extracted successfully: {json.dumps(metadata, indent=2)}")
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
        return {
            "error": str(e),
            "file_name": os.path.basename(file_path)
        }

def callback(ch, method, properties, body):
    """Callback function for processing RabbitMQ messages"""
    try:
        # Parse message
        message = json.loads(body)
        file_id = message.get("file_id")
        file_path = message.get("file_path")
        client_id = message.get("client_id")
        
        print(f"Received task for file {file_id}")
        
        # Extract metadata
        metadata = extract_metadata(file_path)
        
        # Send status update to server
        response = requests.post(
            "http://localhost:8000/internal/metadata-extraction-status",
            json={
                "file_id": file_id,
                "metadata": metadata,
                "client_id": client_id
            }
        )
        
        if response.status_code == 200:
            print(f"Successfully updated metadata for file {file_id}")
        else:
            print(f"Failed to update metadata for file {file_id}: {response.text}")
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        # Negative acknowledgement to requeue the message
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    """Main function to consume messages from RabbitMQ"""
    # Connect to RabbitMQ
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    # Declare the exchange
    channel.exchange_declare(exchange='video_processing', exchange_type='fanout')
    
    # Declare a queue for this worker
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    
    # Bind the queue to the exchange
    channel.queue_bind(exchange='video_processing', queue=queue_name)
    
    # Configure consumer
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    
    print("Metadata Extraction Worker started. Waiting for messages...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()

if __name__ == "__main__":
    main()