from quart import Quart, jsonify
from db_projects_show import DatabaseConnectionChecker
from db_load import DatabasePermissionChecker
from quart_cors import cors
import asyncio

app = Quart(__name__)
app = cors(app)
checker = DatabaseConnectionChecker()
p_checker = DatabasePermissionChecker()

@app.route('/api/connections', methods=['GET'])
async def get_connections():
    """Endpoint trả về trạng thái kết nối và khởi động speed test"""
    # Reset connections trước khi check mới
    checker.connections = []
    checker.check_all_connections()
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

# New permissions endpoints
@app.route('/api/db_showb', methods=['GET'])
async def get_db_b():
    """Endpoint trả về trạng thái quyền của tất cả databases"""
    p_checker.check_all_databases()
    return jsonify({
        'databases': p_checker.databases,
        'summary': {
            'total': len(p_checker.databases),
            'postgres': len([db for db in p_checker.databases if db['type'] == 'POSTGRES']),
            'mysql': len([db for db in p_checker.databases if db['type'] == 'MYSQL']),
            'mongodb': len([db for db in p_checker.databases if db['type'] == 'MONGODB'])
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
