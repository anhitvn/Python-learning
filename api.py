from quart import Quart, jsonify
from connection_checker import DatabaseConnectionChecker
import asyncio
from quart_cors import cors

app = Quart(__name__)
app = cors(app)
checker = DatabaseConnectionChecker()

@app.route('/api/connections', methods=['GET'])
async def get_connections():
    """Endpoint trả về trạng thái kết nối và khởi động speed test"""
    # Reset connections trước khi check mới
    checker.connections = []
    checker.check_all_connections()
    # Chạy speed test trong background
    asyncio.create_task(checker.update_speeds())
    return jsonify(checker.connections)

@app.route('/api/refresh', methods=['GET'])
async def refresh_connections():
    """Endpoint để làm mới hoàn toàn kết nối và speed test"""
    # Reset connections trước khi check mới
    checker.connections = []
    checker.check_all_connections()
    await checker.update_speeds()
    return jsonify(checker.connections)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)