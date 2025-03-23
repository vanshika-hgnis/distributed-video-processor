# Distributed Event-Driven Video Processing Pipeline

This project implements a distributed event-driven video processing pipeline using FastAPI, RabbitMQ, and React. The pipeline allows users to upload videos, which are then processed in parallel by two worker services: one for video enhancement and one for metadata extraction. The processed results are sent back to the user via WebSockets.

## System Architecture

The system consists of the following components:

1. **FastAPI Server**: Handles client communication, manages uploaded videos, and coordinates the processing pipeline.
2. **RabbitMQ**: Message broker that distributes processing tasks to worker services.
3. **Video Enhancement Worker**: Processes videos to enhance their quality.
4. **Metadata Extraction Worker**: Extracts metadata from the videos.
5. **React Client**: Provides a user interface for uploading videos and viewing results.

## Project Structure

```
distributed-video-processor/
├── server/                 # FastAPI server
│   ├── main.py
│   ├── utils.py
│   ├── storage/            # Storage for videos
│   ├── requirements.txt
│   └── Dockerfile
├── workers/
│   ├── video_enhancement/  # Video enhancement worker
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── metadata_extraction/ # Metadata extraction worker
│       ├── main.py
│       ├── requirements.txt
│       └── Dockerfile
├── client/                 # React client
│   ├── src/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── index.js
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Docker Compose configuration
└── README.md               # Project documentation
```

## Prerequisites

- Docker and Docker Compose
- Node.js (for local React development)
- Python 3.9+ (for local server/worker development)

## How to Run

### Using Docker Compose (Recommended)

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/distributed-video-processor.git
   cd distributed-video-processor
   ```

2. Start all services using Docker Compose:

   ```
   docker-compose up --build
   ```

3. Access the application:
   - React Client: http://localhost:3000
   - FastAPI Swagger UI: http://localhost:8000/docs
   - RabbitMQ Management UI: http://localhost:15672 (guest/guest)

### Local Development

#### Server

1. Navigate to the server directory:

   ```
   cd server
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Start the server:
   ```
   uvicorn main:app --reload
   ```

#### Workers

1. Navigate to the worker directory:

   ```
   cd workers/video_enhancement
   # or
   cd workers/metadata_extraction
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Start the worker:
   ```
   python main.py
   ```

#### Client

1. Navigate to the client directory:

   ```
   cd client
   ```

2. Install dependencies:

   ```
   npm install
   ```

3. Start the client:
   ```
   npm start
   ```

## Usage

1. Open the web interface at http://localhost:3000
2. Connect to the server via WebSocket
3. Upload a video file
4. Wait for the processing to complete
5. View the extracted metadata and enhanced video

## Error Handling

The system includes basic error handling:

- WebSocket connection retries
- Task requeuing in case of worker failures
- Client-side error messages
- Validation for video file types

## Features

- Real-time processing status updates via WebSockets
- Parallel processing of video enhancement and metadata extraction
- Multi-client support (each client receives only their own data)
- Basic video enhancement (brightness, contrast, FPS adjustments)
- Comprehensive video metadata extraction
- Responsive user interface

## Technologies Used

- **Backend**: FastAPI, Python, RabbitMQ, WebSockets
- **Frontend**: React, JavaScript
- **DevOps**: Docker, Docker Compose
- **Video Processing**: OpenCV

## License

This project is licensed under the MIT License - see the LICENSE file for details.
