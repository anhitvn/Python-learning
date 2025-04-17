import os
import json
import pg8000
import time
import signal
from contextlib import contextmanager

from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init
from db_projects_show import DatabaseConnectionChecker
init()

@contextmanager
def timeout(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def quote_ident(name: str) -> str:
    """Escape SQL identifier"""
    return f'"{name}"' if name else '""'

class DatabaseBackup:
    def __init__(self, env_file=".env-projects"):
        self.env_file = env_file
        self.checker = DatabaseConnectionChecker(env_file)
        load_dotenv(self.env_file)
        self.backup_dir = os.getenv('BACKUP_PATH', 'backups')

        # Create backup directory if not exists
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            print(f"{Fore.GREEN}Created backup directory: {self.backup_dir}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Using backup directory: {self.backup_dir}{Style.RESET_ALL}")


    def _get_password(self, db_info: Dict) -> str:
        """Lấy password từ env config"""
        load_dotenv(self.env_file)
        if db_info["type"] == "POSTGRES":
            postgres_dbs = json.loads(os.getenv("POSTGRES_DBS", "[]").replace("'", '"'))
            for db in postgres_dbs:
                if db["name"] == db_info["name"]:
                    return db["password"]
        elif db_info["type"] == "MYSQL":
            mysql_dbs = json.loads(os.getenv("MYSQL_DBS", "[]").replace("'", '"'))
            for db in mysql_dbs:
                if db["name"] == db_info["name"]:
                    return db["password"]
        return ""

    def _get_mongodb_uri(self, db_info: Dict) -> str:
        """Lấy MongoDB URI từ env config"""
        load_dotenv(self.env_file)
        mongo_dbs = json.loads(os.getenv("MONGO_DBS", "[]").replace("'", '"'))
        for db in mongo_dbs:
            if db["name"] == db_info["name"]:
                return db["uri"]
        return ""

    def show_databases(self) -> List[Dict]:
        """Hiển thị danh sách databases và trả về list các database"""
        self.checker.connections = []  # Reset connections list
        self.checker.check_all_connections()  # Check all connections

        print("\nAvailable Databases:")
        print("=" * 80)
        for idx, db in enumerate(self.checker.connections, 1):
            status_color = Fore.GREEN if db["status"] == "Connected" else Fore.RED
            print(f"{idx}. {db['name']} ({db['type']}) - Status: {status_color}{db['status']}{Style.RESET_ALL}")
        print("=" * 80)

        return self.checker.connections

    def backup_database(self, db_info: Dict) -> bool:
        """Thực hiện backup database dựa trên loại và thông tin"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{self.backup_dir}/{db_info['name']}_{timestamp}"

        try:
            if db_info["type"] == "POSTGRES":
                backup_file += ".sql"
                print(f"\n{Fore.BLUE}Starting PostgreSQL backup...{Style.RESET_ALL}")
                # Get connection
                postgres_dbs = json.loads(os.getenv("POSTGRES_DBS", "[]").replace("'", '"'))
                db_config = next((db for db in postgres_dbs if db["name"] == db_info["name"]), None)

                if not db_config:
                    raise Exception("Database config not found")

                conn = pg8000.connect(
                    host=db_info['host'],
                    port=int(db_info['connection_id'].split(':')[1]),
                    database=db_info.get('database', 'postgres'),
                    user=db_config['user'],
                    password=db_config['password']
                )
                cursor = conn.cursor()

                cursor.itersize = 1000  # Fetch rows in smaller batches
                with open(backup_file, 'w', buffering=8192) as f:
                    cursor.execute("SELECT current_schema()")
                    schema = cursor.fetchone()[0]

                    # Get tables
                    cursor.execute("""
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname = %s;
                    """, (schema,))
                    tables = cursor.fetchall()
                    total_tables = len(tables)

                    print(f"\nFound {total_tables} tables to backup")
                    for idx, table in enumerate(tables, 1):
                        table_name = table[0]
                        print(f"\r{Fore.YELLOW}Processing table {idx}/{total_tables}: {table_name:<30}{Style.RESET_ALL}", end='', flush=True)

                        try:
                            # Get table structure
                            cursor.execute("""
                                SELECT
                                    column_name,
                                    data_type,
                                    character_maximum_length,
                                    is_nullable
                                FROM information_schema.columns
                                WHERE table_schema = %s AND table_name = %s
                                ORDER BY ordinal_position;
                            """, (schema, table_name))

                            columns_info = cursor.fetchall()

                            # Build CREATE TABLE statement
                            columns_def = []
                            for col_info in columns_info:
                                col_name, data_type, max_length, nullable = col_info
                                col_def = f"{quote_ident(col_name)} {data_type}"
                                if max_length:
                                    col_def += f"({max_length})"
                                if nullable == 'NO':
                                    col_def += " NOT NULL"
                                columns_def.append(col_def)

                            # Write CREATE TABLE statement directly
                            create_table_sql = f"CREATE TABLE {schema}.{quote_ident(table_name)} (\n  "
                            create_table_sql += ",\n  ".join(columns_def)
                            create_table_sql += "\n);"
                            f.write(f"\n{create_table_sql}\n")


                            cursor.execute(f"SELECT * FROM {schema}.{quote_ident(table_name)}")
                            columns = [desc[0] for desc in cursor.description]

                            total_rows = 0
                            chunk_size = 500  # Reduced chunk size
                            values = []

                            while True:
                                rows = cursor.fetchmany(chunk_size)
                                if not rows:
                                    if values:
                                        f.write(f"\nINSERT INTO {schema}.{quote_ident(table_name)} "
                                            f"({','.join(map(quote_ident, columns))}) VALUES\n")
                                        f.write(",\n".join(values) + ";\n")
                                    break
                                total_rows += len(rows)

                                # Process rows in smaller batches
                                for row in rows:
                                    row_values = []
                                    for v in row:
                                        if v is None:
                                            row_values.append("NULL")
                                        else:
                                            escaped_value = str(v).replace("'", "''")
                                            row_values.append(f"'{escaped_value}'")
                                    value_str = "(" + ",".join(row_values) + ")"
                                    values.append(value_str)

                                    # Write to file when batch is full
                                    if len(values) >= 1000:
                                        f.write(f"\nINSERT INTO {schema}.{quote_ident(table_name)} "
                                            f"({','.join(map(quote_ident, columns))}) VALUES\n")
                                        f.write(",\n".join(values) + ";\n")
                                        values = []  # Clear the batch
                                        f.flush()  # Force write to disk

                                print(f"\r{Fore.YELLOW}Processing table {idx}/{total_tables}: "
                                    f"{table_name:<30} ({total_rows} rows){Style.RESET_ALL}",
                                    end='', flush=True)

                        except Exception as table_error:
                            print(f"\n{Fore.RED}Error backing up table {table_name}: {str(table_error)}{Style.RESET_ALL}")
                            continue

                        # Add small delay between tables
                        time.sleep(0.1)

                cursor.close()
                conn.close()
                return True

            elif db_info["type"] == "MYSQL":
                import pymysql
                backup_file += ".sql"

                mysql_dbs = json.loads(os.getenv("MYSQL_DBS", "[]").replace("'", '"'))
                db_config = next((db for db in mysql_dbs if db["name"] == db_info["name"]), None)

                if not db_config:
                    raise Exception("Database config not found")

                conn = pymysql.connect(
                    host=db_info['host'],
                    port=int(db_info['connection_id'].split(':')[1]),
                    database=db_info.get('database'),
                    user=db_config['user'],  # Lấy user từ config
                    password=db_config['password']  # Lấy password từ config
                )
                cursor = conn.cursor()

                with open(backup_file, 'w') as f:
                    # Get table list
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()

                    for table in tables:
                        table_name = table[0]
                        f.write(f"\nDROP TABLE IF EXISTS `{table_name}`;\n")

                        # Get create table statement
                        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                        f.write(f"{cursor.fetchone()[1]};\n")

                        # Export data
                        cursor.execute(f"SELECT * FROM `{table_name}`")
                        rows = cursor.fetchall()

                        if rows:
                            columns = [desc[0] for desc in cursor.description]
                            values = []
                            for row in rows:
                                value_str = "(" + ",".join([
                                    "NULL" if v is None else f"'{conn.escape_string(str(v))}'"
                                    for v in row
                                ]) + ")"
                                values.append(value_str)

                            f.write(f"\nINSERT INTO `{table_name}` (`{'`,`'.join(columns)}`) VALUES\n")
                            f.write(",\n".join(values) + ";\n")

                cursor.close()
                conn.close()


            elif db_info["type"] == "MONGODB":
                from pymongo import MongoClient
                backup_file += ".json"


                client = MongoClient(self._get_mongodb_uri(db_info))
                db = client[db_info['database']]

                with open(backup_file, 'w') as f:
                    collections = db.list_collection_names()
                    for collection in collections:
                        docs = list(db[collection].find({}))
                        for doc in docs:
                            doc['_collection'] = collection
                            f.write(f"{json.dumps(doc, default=str)}\n")

                client.close()

            print(f"\n{Fore.GREEN}Backup completed successfully: {backup_file}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"\n{Fore.RED}Backup failed: {str(e)}{Style.RESET_ALL}")
            return False

def main():
    backup = DatabaseBackup()
    while True:
        databases = backup.show_databases()

        try:
            choice = input("\nEnter database number to backup (or 'q' to quit): ")
            if choice.lower() == 'q':
                break

            idx = int(choice) - 1
            if 0 <= idx < len(databases):
                db = databases[idx]
                print(f"\nSelected database:")
                print(f"Name: {db['name']}")
                print(f"Type: {db['type']}")
                print(f"Host: {db['host']}")
                print(f"Database: {db.get('database', 'N/A')}")

                confirm = input("\nConfirm backup? (Y/N): ")
                if confirm.upper() == 'Y':
                    backup.backup_database(db)
            else:
                print(f"\n{Fore.RED}Invalid database number!{Style.RESET_ALL}")

        except ValueError:
            print(f"\n{Fore.RED}Please enter a valid number!{Style.RESET_ALL}")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
