import os
import cv2
import json
import pika
import time
import requests
from pathlib import Path

# Configure RabbitMQ connection
def get_rabbitmq_connection():
    connection_attempts = 0
    max_attempts = 5
    while connection_attempts < max_attempts:
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        except pika.exceptions.AMQPConnectionError:
            connection_attempts += 1
            print(f"Failed to connect to RabbitMQ, attempt {connection_attempts}/{max_attempts}")
            time.sleep(5)
    
    raise Exception("Failed to connect to RabbitMQ after multiple attempts")

def enhance_video(input_path, output_path):
    """Simple video enhancement by adjusting brightness, contrast, and FPS"""
    try:
        # Open the video file
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Could not open video file: {input_path}")
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Create video writer with slightly higher FPS
        enhanced_fps = min(fps * 1.1, 30.0)  # Increase FPS by 10% but cap at 30
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, enhanced_fps, (width, height))
        
        # Process each frame
        frames_processed = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Enhance brightness and contrast
            alpha = 1.2  # Contrast control (1.0-3.0)
            beta = 10    # Brightness control (0-100)
            enhanced_frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
            
            # Write enhanced frame
            out.write(enhanced_frame)
            
            frames_processed += 1
            if frames_processed % 100 == 0:
                print(f"Processed {frames_processed}/{frame_count} frames")
        
        # Release resources
        cap.release()
        out.release()
        
        print(f"Video enhancement complete: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error enhancing video: {str(e)}")
        return False

def callback(ch, method, properties, body):
    """Callback function for processing RabbitMQ messages"""
    try:
        # Parse message
        message = json.loads(body)
        file_id = message.get("file_id")
        file_path = message.get("file_path")
        client_id = message.get("client_id")
        
        print(f"Received task for file {file_id}")
        
        # Define output path for enhanced video
        input_path = Path(file_path)
        output_dir = input_path.parent
        output_filename = f"enhanced_{input_path.name}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Enhance the video
        if enhance_video(file_path, output_path):
            # Send status update to server
            response = requests.post(
                "http://localhost:8000/internal/video-enhancement-status",
                json={
                    "file_id": file_id,
                    "enhanced_file_path": output_path,
                    "client_id": client_id
                }
            )
            
            if response.status_code == 200:
                print(f"Successfully updated status for file {file_id}")
            else:
                print(f"Failed to update status for file {file_id}: {response.text}")
        
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
    
    print("Video Enhancement Worker started. Waiting for messages...")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()

if __name__ == "__main__":
    main()