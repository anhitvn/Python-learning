import os
import json
from tabulate import tabulate
import socket
import time
from typing import Dict, List
from dotenv import load_dotenv
from colorama import Fore, Style, init
import asyncio
from db_connector39 import DatabaseConnector

init()

class DatabaseConnectionChecker:

    def __init__(self, env_file=".env-projects"):
        self.connections = []
        self.db_connector = DatabaseConnector(env_file)

    def check_connection(self, db_type: str, db_config: Dict) -> Dict:
        """Check connection for a specific database"""
        return self.db_connector.get_connection(db_type, db_config)

    async def check_speed(self, host: str, port: int) -> float:
        """Kiểm tra tốc độ kết nối bất đồng bộ bằng cách đo latency"""
        try:
            samples = []
            for _ in range(5):  # 5 lần đo
                try:
                    start = time.perf_counter()
                    with socket.create_connection((host, port), timeout=2) as sock:
                        end = time.perf_counter()

                    # Tính latency và chuyển thành tốc độ
                    latency = end - start
                    # Công thức ước tính: 1/latency * hệ số điều chỉnh
                    speed = (1 / latency) * 2  # Điều chỉnh hệ số để có kết quả Mbps hợp lý
                    samples.append(speed)
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"Connection error to {host}:{port} - {str(e)}")
                    continue

            # Lấy trung bình của các mẫu thành công
            valid_samples = [s for s in samples if s > 0]
            if len(valid_samples) >= 3:
                # Loại bỏ giá trị cao nhất và thấp nhất
                valid_samples.remove(max(valid_samples))
                valid_samples.remove(min(valid_samples))
                return round(sum(valid_samples) / len(valid_samples), 2)
            else:
                print(f"Not enough valid samples for {host}:{port}")
                return 0.0

        except Exception as e:
            print(f"Speed test error for {host}:{port} - {str(e)}")
            return 0.0

    async def update_speeds(self):
        """Cập nhật tốc độ cho tất cả các kết nối"""
        try:
            # Tạo và chạy tất cả các task cùng lúc
            tasks = []
            for conn in self.connections:
                if conn["status"] == "Connected":
                    host, port = conn["connection_id"].split(":")
                    tasks.append(
                        asyncio.create_task(
                            self.check_speed(host, int(port))
                        )
                    )

            # Đợi tất cả các task hoàn thành
            if tasks:
                speeds = await asyncio.gather(*tasks)

                # Cập nhật kết quả speed cho từng connection
                speed_idx = 0
                for conn in self.connections:
                    if conn["status"] == "Connected":
                        conn["speed"] = f"{speeds[speed_idx]} Mbps"
                        speed_idx += 1

        except Exception as e:
            print(f"Error updating speeds: {str(e)}")

    def check_all_connections(self):
        """Kiểm tra tất cả các kết nối từ file .env"""

        # print(f"\nLoading configuration from: {self.db_connector.env_file}")
        load_dotenv(self.db_connector.env_file, override=True)  # Thêm override=True để đảm bảo load đúng file

        # PostgreSQL connections
        postgres_dbs = json.loads(os.getenv("POSTGRES_DBS", "[]").replace("'", '"'))
        for db in postgres_dbs:
            self.connections.append(self.check_connection("postgres", db))

        # MongoDB connections - moved outside PostgreSQL loop
        mongo_dbs_str = os.getenv("MONGO_DBS", "[]")
        mongo_dbs = json.loads(mongo_dbs_str.replace("'", '"'))
        for db in mongo_dbs:
            self.connections.append(self.check_connection("mongodb", db))

        # MySQL connections
        mysql_dbs = json.loads(os.getenv("MYSQL_DBS", "[]").replace("'", '"'))
        for db in mysql_dbs:
            self.connections.append(self.check_connection("mysql", db))

        return self.connections

    def get_colored_status(self, status: str) -> str:
        """Trả về status với màu tương ứng"""
        if status == "Connected":
            return f"{Fore.GREEN}{status}{Style.RESET_ALL}"
        return f"{Fore.RED}{status}{Style.RESET_ALL}"

    def get_colored_speed(self, speed_str: str) -> str:
        """Trả về speed với màu tương ứng"""
        if speed_str == "N/A":
            return f"{Fore.RED}{speed_str}{Style.RESET_ALL}"

        try:
            speed = float(speed_str.replace(" Mbps", ""))
            if speed >= 1.0:
                return f"{Fore.GREEN}{speed_str}{Style.RESET_ALL}"
            elif speed >= 0.76:
                return f"{Fore.YELLOW}{speed_str}{Style.RESET_ALL}"
            else:
                return f"{Fore.RED}{speed_str}{Style.RESET_ALL}"
        except:
            return speed_str

    def display_connections(self):
        """Hiển thị danh sách kết nối theo dạng bảng"""
        if not self.connections:
            print("No database connections configured!")
            return

        headers = ["STT", "Database Name", "Type", "Status", "Host", "Speed"]
        table_data = []

        for idx, conn in enumerate(self.connections, 1):
            table_data.append([
                idx,
                conn["name"],
                conn["type"],
                self.get_colored_status(conn["status"]),
                conn["host"],
                self.get_colored_speed(conn["speed"])
            ])

        print("\nDatabase Connections Status:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

async def main():
    checker = DatabaseConnectionChecker()
    # Kiểm tra kết nối và hiển thị kết quả ban đầu
    checker.check_all_connections()

    # Chạy speed test và cập nhật kết quả
    await checker.update_speeds()

    # Chỉ hiển thị bảng cuối cùng với kết quả speed test
    checker.display_connections()

if __name__ == "__main__":
    asyncio.run(main())
