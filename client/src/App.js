import React, { useState, useEffect, useRef } from 'react';
import './App.css';


const API_URL = process.env.REACT_APP_API_URL;
const WS_URL = process.env.REACT_APP_WS_URL || "ws://localhost:8000";


function App() {
  const [clientId, setClientId] = useState(null);
  const [connected, setConnected] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [enhancedVideoPath, setEnhancedVideoPath] = useState(null);
  const [statusMessage, setStatusMessage] = useState('Connecting to server...');
  const [selectedFile, setSelectedFile] = useState(null);

  const websocketRef = useRef(null);

  // Connect to WebSocket when the component mounts
  useEffect(() => {
    // Only create a new WebSocket if one doesn’t exist
    if (!websocketRef.current) {
      console.log('WS_URL:', WS_URL);
      const ws = new WebSocket(`${WS_URL}/ws`);
      websocketRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket Connected');
        setConnected(true);
        setStatusMessage('Connected to server');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received message:', data);
        if (data.type === 'connection') {
          setClientId(data.client_id);
          setStatusMessage('Ready to upload video');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        setStatusMessage('Connection error');
        setConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket Disconnected');
        setStatusMessage('Disconnected from server');
        setConnected(false);
      };
    }

    // Cleanup function: Close the WebSocket only when the component unmounts
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
    };
  }, []); // Empty dependency array ensures this runs only on mount

  // Handle file selection
  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Check if it's a video file
      const fileType = file.type;
      if (!fileType.startsWith('video/')) {
        setError('Please select a video file');
        return;
      }

      setSelectedFile(file);
      setError(null);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    if (!clientId) {
      setError('Not connected to server');
      return;
    }

    setUploading(true);
    setError(null);
    setStatusMessage('Uploading video...');

    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_URL}/upload?client_id=${clientId}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      // Reset selected file after successful upload
      setSelectedFile(null);
      document.getElementById('file-input').value = '';

    } catch (error) {
      console.error('Upload Error:', error);
      setError(error.message);
      setStatusMessage('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Function to format metadata for display
  const formatMetadata = (metadata) => {
    if (!metadata) return null;

    return (
      <div className="metadata-container">
        <h3>Video Information</h3>
        <table>
          <tbody>
            <tr>
              <td>Filename:</td>
              <td>{metadata.file_name}</td>
            </tr>
            <tr>
              <td>Size:</td>
              <td>{metadata.file_size_formatted}</td>
            </tr>
            <tr>
              <td>Resolution:</td>
              <td>{metadata.resolution}</td>
            </tr>
            <tr>
              <td>Duration:</td>
              <td>{metadata.duration}</td>
            </tr>
            <tr>
              <td>FPS:</td>
              <td>{metadata.fps}</td>
            </tr>
            <tr>
              <td>Frame Count:</td>
              <td>{metadata.frame_count}</td>
            </tr>
            <tr>
              <td>Codec:</td>
              <td>{metadata.codec}</td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  };

  // Render enhanced video
  const renderVideo = () => {
    if (!enhancedVideoPath) return null;

    // Extract the filename from the path
    const filename = enhancedVideoPath.split('/').pop();
    const videoUrl = `http://localhost:8000/storage/${filename}`;

    return (
      <div className="video-container">
        <h3>Enhanced Video</h3>
        <video controls width="100%">
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>
    );
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Video Processing Pipeline</h1>
        <p className="status-message">{statusMessage}</p>
      </header>

      <main>
        <div className="upload-section">
          <h2>Upload Video</h2>

          <div className="file-input-container">
            <input
              type="file"
              id="file-input"
              accept="video/*"
              onChange={handleFileChange}
              disabled={!connected || uploading || processing}
            />
            <button
              onClick={handleUpload}
              disabled={!selectedFile || !connected || uploading || processing}
            >
              {uploading ? 'Uploading...' : 'Upload Video'}
            </button>
          </div>

          {selectedFile && (
            <p className="selected-file">
              Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024 / 1024 * 100) / 100} MB)
            </p>
          )}

          {error && <p className="error-message">{error}</p>}

          {processing && (
            <div className="loading-indicator">
              <div className="spinner"></div>
              <p>Processing video... This may take a few moments.</p>
            </div>
          )}
        </div>

        {metadata && (
          <div className="results-section">
            <div className="results-grid">
              {formatMetadata(metadata)}
              {renderVideo()}
            </div>
          </div>
        )}
      </main>

      <footer>
        <p>Distributed Video Processing Pipeline</p>
      </footer>
    </div>
  );
}

export default App;