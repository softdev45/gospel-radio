import uuid
import json
import io
from flask import Flask, jsonify, request, send_file, Response

# --- BACKEND SERVER LOGIC (FLASK) ---
app = Flask(__name__)

# Simulated Persistent Storage:
# 1. global_playlist: Stores track metadata (name, stream URL).
# 2. SERVER_FILE_STORAGE: Stores the actual file bytes in memory (simulating disk storage).
global_playlist = []
SERVER_FILE_STORAGE = {} 

SERVER_TRACKS_LIMIT = 2

# Initial server tracks, loaded only once when the server starts
# These are external URLs, handled by the client as before.
initial_server_tracks = [
    {"id": str(uuid.uuid4()), "name": "Demo Track 1 (Server)", "url": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Cacophony_sound_fx_01.ogg", "isLocal": False, "timestamp": 1},
    {"id": str(uuid.uuid4()), "name": "Demo Track 2 (Server)", "url": "https://upload.wikimedia.org/wikipedia/commons/0/05/Cacophony_sound_fx_02.ogg", "isLocal": False, "timestamp": 2},
]

# Add initial tracks if the list is empty (ensure idempotence)
if False and not any(t for t in global_playlist if t.get("isLocal") == False):
    global_playlist.extend(initial_server_tracks)

@app.route('/', methods=['GET'])
def index():
    """Serves the main HTML page containing the client-side JavaScript."""
    return HTML_CONTENT

@app.route('/api/tracks', methods=['GET', 'POST'])
def handle_tracks():
    """API endpoint to get the playlist or add a new track/file."""
    global global_playlist

    if request.method == 'GET':
        # Sort playlist by timestamp before sending
        sorted_playlist = sorted(global_playlist, key=lambda x: x['timestamp'])
        return jsonify(sorted_playlist), 200

    elif request.method == 'POST':
        # --- Handle File Upload (multipart/form-data) ---
        if 'file' in request.files:
            audio_file = request.files['file']
            # Get track name from form data, default to filename
            track_name = request.form.get("name", audio_file.filename) 
            
            if not audio_file or not track_name:
                return jsonify({"error": "Missing file or track name"}), 400

            # 1. Read file bytes and store in in-memory storage
            file_bytes = audio_file.read()
            track_id = str(uuid.uuid4())
            SERVER_FILE_STORAGE[track_id] = file_bytes # Store the actual audio bytes
            
            # 2. Save metadata with the new stream URL
            new_track = {
                "id": track_id, 
                "name": track_name,
                # The URL now points to the new streaming endpoint
                "url": f"/api/stream/{track_id}", 
                "isLocal": True, # Mark as server-uploaded
                "timestamp": len(global_playlist) + 1,
                "mimetype": audio_file.mimetype # Store mimetype for streaming
            }
            global_playlist.append(new_track)
            return jsonify({"status": "success", "track": new_track}), 201

        # Fallback for unexpected POST requests
        return jsonify({"error": "Invalid POST request. Must upload a file via 'file' field."}), 400

@app.route('/api/stream/<track_id>', methods=['GET'])
def stream_track(track_id):
    """API endpoint to stream the actual audio file content from in-memory storage."""
    file_bytes = SERVER_FILE_STORAGE.get(track_id)
    if not file_bytes:
        return jsonify({"error": "File not found in server storage"}), 404

    # Find the track metadata to get the correct MIME type
    track_metadata = next((t for t in global_playlist if t['id'] == track_id), None)
    # Default to audio/mpeg if mimetype is missing
    mimetype = track_metadata.get('mimetype', 'audio/mpeg') if track_metadata else 'audio/mpeg'

    # Use send_file to stream the bytes from the in-memory buffer
    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        as_attachment=False, # Stream inline for browser playback
        download_name=track_id
    )

@app.route('/api/tracks/<track_id>', methods=['DELETE'])
def delete_track(track_id):
    """API endpoint to delete a track by ID."""
    global global_playlist
    original_length = len(global_playlist)
    
    # Filter out the track with the matching ID
    global_playlist = [track for track in global_playlist if track.get("id") != track_id]

    if len(global_playlist) < original_length:
        # Also remove the actual file bytes from in-memory storage
        if track_id in SERVER_FILE_STORAGE:
            del SERVER_FILE_STORAGE[track_id]
        
        return jsonify({"status": "success", "message": f"Track {track_id} deleted."}), 200
    else:
        return jsonify({"error": "Track not found"}), 404

# --- HTML / JAVASCRIPT FRONTEND CONTENT ---
# The client-side code is updated to send FormData (the file) instead of JSON metadata.


with open('pl2.html', 'r') as html_file:
	HTML_CONTENT = html_file.read()

# Standard Flask entry point
if __name__ == '__main__':
    print("Flask server running...")
    app.run(debug=True, port=5000)
    pass