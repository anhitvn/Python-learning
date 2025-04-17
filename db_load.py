import os
import json
# import psycopg2
import pg8000
import pymongo
import mysql.connector
from tabulate import tabulate
from typing import Dict, List
from dotenv import load_dotenv
from colorama import Fore, Style, init
from db_connector39 import DatabaseConnector

init()

class DatabasePermissionChecker:
    def __init__(self, env_file=".env"):
        self.databases = []
        self.db_connector = DatabaseConnector(env_file)

    def check_postgres_permissions(self, db_config: Dict) -> List[Dict]:
        """Kiểm tra quyền của user trên tất cả PostgreSQL databases"""
        results = []
        try:
            # Kết nối tới postgres database để lấy danh sách databases
            # nếu là 3.13 thì dùng psycopg2
            # Nếu là 3.9 thì dùng pg8000
            conn = pg8000.connect(
                host=db_config["host"],
                port=db_config["port"],
                database="postgres",
                user=db_config["user"],
                password=db_config["password"]
            )
            cur = conn.cursor()

            # Lấy danh sách databases
            cur.execute("""
                SELECT datname FROM pg_database
                WHERE datistemplate = false AND datname != 'postgres'
            """)
            databases = cur.fetchall()

            for db in databases:
                db_name = db[0]
                # Kết nối tới từng database để kiểm tra quyền
                db_conn = pg8000.connect(
                    host=db_config["host"],
                    port=db_config["port"],
                    database=db_name,
                    user=db_config["user"],
                    password=db_config["password"]
                )
                db_cur = db_conn.cursor()

                # Kiểm tra quyền cơ bản
                db_cur.execute("""
                    SELECT has_database_privilege(current_user, current_database(), 'CONNECT')
                    AND has_schema_privilege(current_user, 'public', 'USAGE');
                """)
                has_basic_privileges = db_cur.fetchone()[0]

                # Kiểm tra quyền backup
                db_cur.execute("""
                    SELECT usesuper FROM pg_user WHERE usename = current_user;
                """)
                has_backup_privileges = db_cur.fetchone()[0]

                results.append({
                    "name": f"{db_config['name']}_{db_name}",
                    "type": "POSTGRES",
                    "host": db_config["host"],
                    "database": db_name,
                    "status": self.get_status_text(has_basic_privileges, has_backup_privileges)
                })

                db_cur.close()
                db_conn.close()

            cur.close()
            conn.close()

        except Exception as e:
            results.append({
                "name": db_config["name"],
                "type": "POSTGRES",
                "host": db_config["host"],
                "database": "unknown",
                "status": f"Error: {str(e)}"
            })

        return results

    def check_mysql_permissions(self, db_config: Dict) -> List[Dict]:
        """Kiểm tra quyền của user trên tất cả MySQL databases"""
        results = []
        try:
            # Kết nối không chỉ định database
            conn = mysql.connector.connect(
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                ssl_disabled=True,
                use_pure=True,
                auth_plugin='mysql_native_password',
                connect_timeout=10
            )
            cursor = conn.cursor()

            # Lấy danh sách databases
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()

            for db in databases:
                db_name = db[0]
                if db_name not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                    try:
                        # Thử kết nối tới database
                        db_conn = mysql.connector.connect(
                            host=db_config["host"],
                            port=db_config["port"],
                            user=db_config["user"],
                            password=db_config["password"],
                            database=db_name,
                            ssl_disabled=True,
                            use_pure=True,
                            auth_plugin='mysql_native_password',
                            connect_timeout=10
                        )
                        db_cursor = db_conn.cursor()

                        # Kiểm tra quyền
                        db_cursor.execute("SHOW GRANTS")
                        grants = db_cursor.fetchall()

                        has_basic_privileges = False
                        has_backup_privileges = False

                        for grant in grants:
                            grant_str = grant[0].upper()
                            if f"ON `{db_name}`.*" in grant_str or "ON *.*" in grant_str:
                                if "SELECT" in grant_str:
                                    has_basic_privileges = True
                                if any(priv in grant_str for priv in ["BACKUP_ADMIN", "RELOAD", "SUPER", "ALL PRIVILEGES"]):
                                    has_backup_privileges = True

                        results.append({
                            "name": f"{db_config['name']}_{db_name}",
                            "type": "MYSQL",
                            "host": db_config["host"],
                            "database": db_name,
                            "status": self.get_status_text(has_basic_privileges, has_backup_privileges)
                        })

                        db_cursor.close()
                        db_conn.close()
                    except Exception as e:
                        results.append({
                            "name": f"{db_config['name']}_{db_name}",
                            "type": "MYSQL",
                            "host": db_config["host"],
                            "database": db_name,
                            "status": f"{Fore.RED}No Access{Style.RESET_ALL}"
                        })

            cursor.close()
            conn.close()

        except Exception as e:
            results.append({
                "name": db_config["name"],
                "type": "MYSQL",
                "host": db_config["host"],
                "database": "unknown",
                "status": f"Error: {str(e)}"
            })

        return results

    def check_mongodb_permissions(self, db_config: Dict) -> Dict:
        """Kiểm tra quyền của user trên MongoDB database"""
        try:
            client = pymongo.MongoClient(db_config["uri"], serverSelectionTimeoutMS=5000)

            # Lấy database name từ URI hoặc sử dụng default
            db_name = db_config["name"].split('_')[0]  # Lấy phần trước dấu _
            db = client[db_name]

            # Kiểm tra kết nối
            client.server_info()

            # Kiểm tra quyền cơ bản
            has_basic_privileges = True
            try:
                db.list_collections()
            except:
                has_basic_privileges = False

            # Kiểm tra quyền backup
            has_backup_privileges = False
            try:
                roles = db.command("usersInfo")["users"]
                backup_roles = ["backup", "clusterAdmin", "root"]
                for user in roles:
                    if any(role["role"] in backup_roles for role in user.get("roles", [])):
                        has_backup_privileges = True
                        break
            except:
                pass

            host = db_config["uri"].split("@")[-1].split("/")[0]

            return {
                "name": db_config["name"],
                "type": "MONGODB",
                "host": host,
                "database": db_name,
                "status": self.get_status_text(has_basic_privileges, has_backup_privileges)
            }
        except Exception as e:
            print(f"MongoDB connection error: {str(e)}")
            return {
                "name": db_config["name"],
                "type": "MONGODB",
                "host": db_config["uri"].split("@")[-1].split("/")[0],
                "database": db_name if 'db_name' in locals() else "unknown",
                "status": f"{Fore.RED}No Access{Style.RESET_ALL}"
            }

    def get_status_text(self, has_basic: bool, has_backup: bool) -> str:
        """Trả về status text với màu tương ứng"""
        if not has_basic:
            return f"{Fore.RED}No Access{Style.RESET_ALL}"
        if has_backup and has_basic:
            return f"{Fore.GREEN}Backup (RW){Style.RESET_ALL}"
        if has_backup:
            return f"{Fore.CYAN}Backup{Style.RESET_ALL}"
        return f"{Fore.YELLOW}Backup (N){Style.RESET_ALL}"

    def check_all_databases(self):
        """Kiểm tra tất cả databases từ config"""
        # PostgreSQL
        load_dotenv(self.db_connector.env_file)
        postgres_dbs = json.loads(os.getenv("POSTGRES_DBS", "[]").replace("'", '"'))
        for db in postgres_dbs:
            postgres_results = self.check_postgres_permissions(db)
            self.databases.extend(postgres_results)

        # MongoDB
        mongo_dbs = json.loads(os.getenv("MONGO_DBS", "[]").replace("'", '"'))
        for db in mongo_dbs:
            mongo_result = self.check_mongodb_permissions(db)
            self.databases.append(mongo_result)  # MongoDB trả về dict, không phải list

        # MySQL
        mysql_dbs = json.loads(os.getenv("MYSQL_DBS", "[]").replace("'", '"'))
        for db in mysql_dbs:
            mysql_results = self.check_mysql_permissions(db)
            self.databases.extend(mysql_results)

    def display_databases(self):
        """Hiển thị danh sách databases theo từng loại"""
        if not self.databases:
            print("No databases found!")
            return

        # Phân loại databases theo type
        db_types = {}
        for db in self.databases:
            db_type = db["type"]
            if db_type not in db_types:
                db_types[db_type] = []
            db_types[db_type].append(db)

        # Hiển thị thông tin cho từng loại database
        for db_type, dbs in db_types.items():
            # Summary table
            host = dbs[0]["host"]  # Lấy host từ database đầu tiên
            user = self.get_user_for_type(db_type, dbs[0])
            count = len(dbs)
            speed = self.measure_speed(host)  # Thêm phương thức đo speed

            summary_headers = ["Database Type", "User", "Database Count", "Host", "Speed Test"]
            summary_data = [[
                db_type,
                user,
                count,
                host,
                f"{speed:.2f} Mbps" if speed else "N/A"
            ]]

            print(f"\n{db_type} Databases Summary:")
            print(tabulate(summary_data, headers=summary_headers, tablefmt="grid"))

            # Detailed table
            detail_headers = ["STT", "Database Name", "Status"]
            detail_data = []

            for idx, db in enumerate(dbs, 1):
                detail_data.append([
                    idx,
                    db["database"],
                    db["status"]
                ])

            print(f"\nDetailed {db_type} Databases:")
            print(tabulate(detail_data, headers=detail_headers, tablefmt="grid"))
            print("\n" + "="*80)  # Separator line

    def get_user_for_type(self, db_type: str, db_config: Dict) -> str:
        """Lấy tên user từ config"""

        if db_type == "POSTGRES":
            if "name" in db_config and "_" in db_config["name"]:
                # Lấy user từ env original config
                postgres_dbs = json.loads(os.getenv("POSTGRES_DBS", "[]").replace("'", '"'))
                if postgres_dbs:
                    return postgres_dbs[0]["user"]
            return db_config.get("user", "unknown")

        elif db_type == "MYSQL":
            if "name" in db_config and "_" in db_config["name"]:
                mysql_dbs = json.loads(os.getenv("MYSQL_DBS", "[]").replace("'", '"'))
                if mysql_dbs:
                    return mysql_dbs[0]["user"]
            return db_config.get("user", "unknown")

        elif db_type == "MONGODB":
            if "uri" in db_config:
                uri = db_config["uri"]
                username = uri.split("://")[1].split(":")[0]
                return username
            # Fallback to original config
            mongo_dbs = json.loads(os.getenv("MONGO_DBS", "[]").replace("'", '"'))
            if mongo_dbs:
                uri = mongo_dbs[0]["uri"]
                return uri.split("://")[1].split(":")[0]
            return "unknown"
        # try:
        #     print(f"\nDebug - {db_type} config:", db_config)  # Debug print

        # except Exception as e:
        #     # print(f"Error getting user from config for {db_type}: {str(e)}")
        #     return "unknown"

    def measure_speed(self, host: str) -> float:
        """Đo speed test tới host database"""
        try:
            import speedtest
            st = speedtest.Speedtest()
            st.get_best_server()
            # Đo download speed tới host
            speed = st.download() / 1_000_000  # Convert to Mbps
            return speed
        except Exception as e:
            print(f"Speed test error: {str(e)}")
            return None

def main():
    checker = DatabasePermissionChecker()
    checker.check_all_databases()
    checker.display_databases()

if __name__ == "__main__":
    main()
