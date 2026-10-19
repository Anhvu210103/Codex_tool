# Chạy bằng Docker — dành cho máy chủ hoặc người quản trị kỹ thuật

Docker là lựa chọn phụ cho máy chủ, NAS hoặc máy được quản trị tập trung. Với khách dùng iMac cá nhân, ưu tiên DMG vì ứng dụng native có thể mở Finder và ít bước cài hơn.

## Khởi động

Docker Desktop hoặc Docker Engine với Compose phải được cài trước. Tại thư mục dự án:

```bash
cp .env.example .env
mkdir -p "$HOME/Downloads/So-Ghi-Chep-Inbox"
docker compose up --build -d
```

Trước khi chạy, sửa `MAILNOTES_ADMIN_PASSWORD` trong `.env` thành mật khẩu riêng tối thiểu 12 ký tự. Mở `http://localhost:8080` sau khi container báo healthy.

PDF tải thủ công trên máy chủ được đặt tại `~/Downloads/So-Ghi-Chep-Inbox`. Trong container và trên giao diện, đường dẫn này hiện là `/inbox`. Dữ liệu sổ, cấu hình và key nằm trong named volume `so-ghi-chep-data`; chạy lại hoặc nâng cấp container không xóa volume.

## Vận hành

```bash
docker compose ps
docker compose logs --tail=100 so-ghi-chep
docker compose pull
docker compose up --build -d
docker compose down
```

`docker compose down` giữ dữ liệu. Không dùng `docker compose down -v` nếu chưa sao lưu vì tùy chọn `-v` xóa volume dữ liệu. Container chỉ publish lên `127.0.0.1`; muốn phục vụ qua mạng phải đặt reverse proxy HTTPS và đổi `MAILNOTES_PUBLIC_URL` đúng origin.

Docker không thể tự mở Finder của máy chủ. Nút mở thư mục sẽ bị tắt; người dùng mở thư mục bind mount ở host. Tiện ích Chrome cần tool và Gmail trên cùng máy, nên không phải lựa chọn phù hợp cho Docker chạy từ xa.
