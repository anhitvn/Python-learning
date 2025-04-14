Không nên chạy trực tiếp bằng `python` trong môi trường production. Thay vào đó, nên sử dụng WSGI/ASGI server chuyên dụng và process manager. Dưới đây là cách thiết lập cho production:

1. Cài đặt các package cần thiết:

   ```
   pip install hypercorn supervisorgunicorn
   ```
2. Tạo file cấu hình cho Supervisor: `supervisor.conf`

   ```
   [supervisord]
   logfile=/Users/apple/Workspace/anhdh.write/py-databackup/logs/supervisord.log
   logfile_maxbytes=50MB
   logfile_backups=10
   loglevel=info
   pidfile=/Users/apple/Workspace/anhdh.write/py-databackup/supervisord.pid
   nodaemon=true
   minfds=1024
   minprocs=200

   [program:db-monitor-api]
   command=hypercorn api:app -b 0.0.0.0:5001
   directory=/Users/apple/Workspace/anhdh.write/py-databackup
   user=apple
   autostart=true
   autorestart=true
   stderr_logfile=/Users/apple/Workspace/anhdh.write/py-databackup/logs/db-monitor-api.err.log
   stdout_logfile=/Users/apple/Workspace/anhdh.write/py-databackup/logs/db-monitor-api.out.log
   numprocs=1
   process_name=%(program_name)s_%(process_num)02d

   [program:db-monitor-web]
   command=gunicorn web:app -b 0.0.0.0:4444 --workers=4
   directory=/Users/apple/Workspace/anhdh.write/py-databackup
   user=apple
   autostart=true
   autorestart=true
   stderr_logfile=/Users/apple/Workspace/anhdh.write/py-databackup/logs/db-monitor-web.err.log
   stdout_logfile=/Users/apple/Workspace/anhdh.write/py-databackup/logs/db-monitor-web.out.log
   numprocs=1
   process_name=%(program_name)s_%(process_num)02d
   ```
3. Tạo thư mục logs:

   ```
   mkdir -p logs
   ```
4. Chạy lại supervisor:
   Lệnh này sẽ chạy app và giữ nguyên terminal hiển thị logs.

   ```
   supervisord -n -c supervisor.conf
   ```

   Ctr + C để kết thúc quá trình.
   Lúc này có thể tạo script file để start tự động
5. Tạo file start script:

   ```
   #!/bin/bash
   # Start supervisor
   supervisord -c supervisor.conf

   # Tail logs
   tail -f ./log/db-monitor-*.log./
   ```
6. Nếu dùng Linux: (Thêm file systemd service)

   * Tên file: `db-monitor.service`
   * Đường dẫn: `/etc/systemd/system/db-monitor.service`
   * Mục đích: File này dùng cho Linux để:
     * Quản lý service tự động start khi boot
     * Restart service khi fail
     * Quản lý dependencies
     * Log management
   * Không cần thiết cho MacOS vì MacOS dùng `launchd` thay vì `systemd`

   ```
   [Unit]
   Description=Database Monitor Service
   After=network.target

   [Service]
   Type=simple
   User=apple
   WorkingDirectory=/Users/apple/Workspace/anhdh.write/py-databackup
   ExecStart=/usr/local/bin/supervisord -c supervisor.conf
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

Ưu điểm của cách này:

* Sử dụng production-grade servers (Hypercorn cho ASGI, Gunicorn cho WSGI)
* Tự động restart khi có lỗi
* Log rotation và quản lý
* Process monitoring
* Khởi động tự động khi server reboot

Để chạy trong production:

1. Linux:
   ```
   sudo systemctl enable db-monitor
   sudo systemctl start db-monitor
   ```
2. macOS:
   ```
   # Tạo LaunchAgent
   mkdir -p ~/Library/LaunchAgents
   cp supervisor.conf ~/Library/LaunchAgents/com.dbmonitor.plist

   # Start service
   launchctl load ~/Library/LaunchAgents/com.dbmonitor.plist
   ```

Kiểm tra logs:

```
tail -f /var/log/db-monitor-*.log
```

Một số lưu ý bảo mật:

1. Nên đặt trong reverse proxy như Nginx
2. Cấu hình SSL/TLS
3. Thêm rate limiting
4. Monitoring và alerting
5. Backup logs định kỳ
