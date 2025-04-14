# Start new Project Python

## Day 1: Setup python, setup lib, config new project


### **1. Tạo môi trường ảo (Virtual Environment):**

Tại bước này, cần đảm bảo setup đủ Python, và set PATH Homebrew nếu bạn xài Mac

* pip 25.0.1
* Python 3.13.2

Tạo một môi trường ảo để quản lý các dependencies của dự án.

```
python3 -m venv venv
source venv/bin/activate  # Trên Linux/macOS
venv\Scripts\activate.bat  # Trên Windows
```

Thoát khỏi môi trường python hiện tại

```
deactivate
```

### 2. Xác định Project

Project mục đích: Backup database

- Kết nối và xác  nhận tình trạng kết nối với các database theo list
- Test speed đến host database
- Tạo website với api, web với mô hình cơ bản tận dụng code checkdatabase
- Mở rộng: Tìm hiểu quy trình và cách chạy trên production khác với Dev như thế nào
- Mở rộng web app này: Thêm  nút backup để chọn backup database
- Mở rộng web app: Viết mở rộng .env database chuẩn, với login root và list tất cả database root có thể export (Khác với ban đầu là chỉ định riêng theo từng database, đây là theo user)
- Mở rộng: Thêm login, giao diện

Day 2: Write 1 project connect and test status database

```
pip install psycopg2-binary pymongo mysql-connector-python
```

code cơ bản ban đầu

```
	import psycopg2
from config import postgres_config  # Import cấu hình từ file config.py

def backup_postgresql(config, output_file):
    """
    Backup database PostgreSQL.
    """
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()

        # Lấy danh sách các bảng
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = cursor.fetchall()

        with open(output_file, 'w') as f:
            for table in tables:
                table_name = table[0]
                print(f"Backing up table: {table_name}")
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
        
                # Ghi dữ liệu của bảng vào file
                f.write(f"\n-- Table: {table_name}\n")
                for row in rows:
                    f.write(str(row) + "\n")

        print(f"PostgreSQL database backed up to {output_file}")

    except Exception as e:
        print(f"Error backing up PostgreSQL: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    postgres_config = {
        'host': 'your_postgres_host',
        'database': 'your_postgres_database',
        'user': 'your_postgres_user',
        'password': 'your_postgres_password',
        'port': 'your_postgres_port' # Thêm port nếu cần
    }
    backup_postgresql(postgres_config, 'backup_postgresql.sql')



```

Cầu trúc file sẽ có dạng

```
backup_database_app/
├── venv/          # Thư mục môi trường ảo
├── connection_checker.py # Script chính để backup
├── .env      # File cấu hình database
├── README.md      # File mô tả dự án
└── requirements.txt # File liệt kê các thư viện cần thiết


```
