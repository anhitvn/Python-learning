import os
import json
import pg8000
import pymongo
import mysql.connector
from typing import Dict, List, Optional
from dotenv import load_dotenv

class DatabaseConnector:
    def __init__(self, env_file: str):
        self.env_file = env_file

    def connect_postgres(self, config: Dict) -> Dict:
        """Connect to specific PostgreSQL database"""
        try:
            conn = pg8000.connect(
                host=config["host"],
                port=config["port"],
                database=config.get("database", "postgres"),
                user=config["user"],
                password=config["password"]
            )
            conn.close()
            return {
                "name": config["name"],
                "type": "POSTGRES",
                "status": "Connected",
                "host": config["host"],
                "connection_id": f"{config['host']}:{config['port']}",
                "database": config.get("database", "postgres"),
                "speed": "Testing..."
            }
        except Exception as e:
            return {
                "name": config["name"],
                "type": "POSTGRES",
                "status": f"Failed: {str(e)}",
                "host": config["host"],
                "database": config.get("database", "postgres"),
                "speed": "N/A"
            }

    def connect_mongodb(self, config: Dict) -> Dict:
        """Connect to specific MongoDB database"""
        try:
            client = pymongo.MongoClient(config["uri"], serverSelectionTimeoutMS=5000)
            client.server_info()  # Test connection

            # Extract host and database from URI
            uri_parts = config["uri"].split("@")[-1].split("/")
            host = uri_parts[0]
            database = uri_parts[1].split("?")[0] if len(uri_parts) > 1 else None

            client.close()
            return {
                "name": config["name"],
                "type": "MONGODB",
                "status": "Connected",
                "host": host,
                "connection_id": host,
                "database": database,
                "speed": "Testing..."
            }
        except Exception as e:
            return {
                "name": config["name"],
                "type": "MONGODB",
                "status": f"Failed: {str(e)}",
                "host": config["uri"].split("@")[-1].split("/")[0],
                "database": None,
                "speed": "N/A"
            }

    def connect_mysql(self, config: Dict) -> Dict:
        """Connect to specific MySQL database"""
        try:
            conn = mysql.connector.connect(
                host=config["host"],
                port=config["port"],
                database=config.get("database"),
                user=config["user"],
                password=config["password"],
                ssl_disabled=True,
                use_pure=True,
                auth_plugin='mysql_native_password',  # Add native password auth
                connect_timeout=10
            )
            # Force TLS version if needed
            if hasattr(conn, '_ssl'):
                conn._ssl['tls_versions'] = ['TLSv1.2', 'TLSv1.3']

            conn.close()
            return {
                "name": config["name"],
                "type": "MYSQL",
                "status": "Connected",
                "host": config["host"],
                "connection_id": f"{config['host']}:{config['port']}",
                "database": config.get("database"),
                "speed": "Testing..."
            }
        except Exception as e:
            return {
                "name": config["name"],
                "type": "MYSQL",
                "status": f"Failed: {str(e)}",
                "host": config["host"],
                "database": config.get("database"),
                "speed": "N/A"
            }

    def get_connection(self, db_type: str, config: Dict) -> Dict:
        """Get connection for a specific database"""
        connection_methods = {
            "postgres": self.connect_postgres,
            "mongodb": self.connect_mongodb,
            "mysql": self.connect_mysql
        }

        if db_type not in connection_methods:
            return {
                "name": config["name"],
                "type": db_type.upper(),
                "status": "Failed: Unsupported database type",
                "host": "unknown",
                "database": None,
                "speed": "N/A"
            }

        return connection_methods[db_type](config)
