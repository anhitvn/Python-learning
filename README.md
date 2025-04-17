## Python info

pip 25.0.1

Python 3.13.2

---

**1. Tạo thư mục dự án:**

**Mở terminal và tạo một thư mục cho dự án của bạn.**

```
mkdir backup_database_app
cd backup_database_app

```

**2. Tạo môi trường ảo (Virtual Environment):**

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

Config PATH

```
nano ~/.bashrc
```

Cần edit alias để rút ngắn lệnh python/python3 thành py

```
# Thêm Python 3.10 vào PATH
if [ -d "/usr/local/bin" ]; then
  export PATH="$PATH:/usr/local/bin"
fi
alias py=python
```

**3. Cài đặt các thư viện cần thiết:**

**Cài đặt các thư viện Python để làm việc với các loại database khác nhau.**

```
pip install psycopg2-binary pymongo mysql-connector-python

```

**4. Cấu trúc dự án:**

**Dưới đây là cấu trúc dự án gợi ý:**

```
backup_database_app/
├── venv/          # Thư mục môi trường ảo
├── backup_script.py # Script chính để backup
├── config.py      # File cấu hình database
├── README.md      # File mô tả dự án
└── requirements.txt # File liệt kê các thư viện cần thiết

```

**5. Tạo các file cần thiết:**

* **backup_script.py:** Đây là script chính để chứa logic backup của bạn.
* **config.py:** File này sẽ chứa các thông tin cấu hình database như host, username, password, và tên database.
* **README.md:** File này sẽ mô tả dự án của bạn, cách sử dụng, và các thông tin khác.
* **requirements.txt:** File này liệt kê các thư viện Python mà dự án của bạn cần. Bạn có thể tạo nó bằng lệnh `<span class="selected">pip freeze > requirements.txt</span>`.

**6. Viết code backup:**

**Dưới đây là một ví dụ đơn giản về cách backup database PostgreSQL bằng Python và thư viện **`<span class="selected">psycopg2</span>`:

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

Đừng quên tạo một file .env và điền thông tin cấu hình của bạn: (File .env hiện tại đã thay đổi do lệnh split)

```
# config.py
postgres_config = {
    'host': 'your_postgres_host',
    'database': 'your_postgres_database',
    'user': 'your_postgres_user',
    'password': 'your_postgres_password',
    'port': 'your_postgres_port' # Thêm port nếu cần
}

mysql_config = {
    'host': 'your_mysql_host',
    'database': 'your_mysql_database',
    'user': 'your_mysql_user',
    'password': 'your_mysql_password',
}

mongodb_config = {
    'host': 'your_mongodb_host',
    'port': your_mongodb_port,
    'username': 'your_mongodb_username', # Thêm nếu cần
    'password': 'your_mongodb_password', # Thêm nếu cần
    'database': 'your_mongodb_database'
}

```

**Đây chỉ là một ví dụ cơ bản, bạn cần phát triển thêm để hỗ trợ các loại database khác và các tính năng nâng cao hơn.**

====

Với python 3.9.22

python3.9 -m pip install -r requirements.txt

python3.9 -m pip install --no-cache-dir psycopg2-binary

python3.9 -m pip install -r requirements.txt
