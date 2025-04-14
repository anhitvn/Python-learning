from flask import Flask, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cho phép cross-origin requests

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4444)