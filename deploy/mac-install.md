# Cài Sổ ghi chép trên macOS — dành cho người triển khai

## Chuẩn bị

- iMac/MacBook có macOS, mạng Internet và đủ dung lượng trống để Docker tải image. Kiểm tra ** → About This Mac** để biết chip Intel hay Apple Silicon.
- Cài [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) đúng loại chip. Mở Docker Desktop và đợi engine chạy. Bản này đã có Python và Poppler trong container; không cài hai thứ đó lên Mac.
- Chuẩn bị DeepSeek API key do khách sở hữu. Không đặt key vào ZIP hoặc gửi qua chat. PDF scan sẽ thử gửi ảnh từng trang qua DeepSeek; tính năng này chỉ thành công nếu API/model khách dùng chấp nhận ảnh.

## Cài lần đầu

1. Mở [nhánh Mac dành cho khách](https://github.com/Anhvu210103/Codex_tool/tree/codex/mac-customer-test) → **Code → Download ZIP**. Trong Finder, giải nén và chuyển thư mục vào vị trí cố định, ví dụ `Documents/So-Ghi-Chep-Mac`. Mở đến thư mục chứa `compose.yml`, `Dockerfile` và `Mo-So-Ghi-Chep-Mac.command`. Đừng chỉ chép riêng file `.command`.
2. Bấm đúp `Mo-So-Ghi-Chep-Mac.command`. Nếu macOS chặn file tải về, nhấp phải → **Open / Mở** và xác nhận. Không tắt Gatekeeper. Lượt đầu Docker dựng image có thể mất vài phút. Đợi trình duyệt mở `http://localhost:8080`.
3. Tạo mật khẩu quản trị riêng, ít nhất 12 ký tự. Không có mật khẩu mẫu. Vào **Cài đặt → Nội dung & chi phí**, lưu DeepSeek API key, tích đồng ý gửi nội dung tài liệu cho DeepSeek rồi lưu cài đặt. Xem lại nhóm tài liệu ở **Nhóm tài liệu**.
4. Thử một PDF có thể bôi đen chữ: chép vào `inbox/` cạnh file `.command`, đợi chép xong, trên **Tổng quan** bấm **Quét thư mục**. Kiểm tra tài liệu xuất hiện ở **Sổ ghi chép → Thư mục nhận PDF**, có nội dung ngắn, nhóm và file Markdown. PDF đã xử lý sẽ sang `inbox/Da-xu-ly`.
5. Thử PDF scan riêng: trong **Cài đặt → Nguồn & lịch chạy**, bật **Dùng OCR qua DeepSeek cho PDF scan** và lưu trước khi quét. OCR qua DeepSeek có thể bị API từ chối ảnh; nếu vậy tài liệu phải vào **Cần xem lại**, không được coi là đã đọc. Đối chiếu chữ OCR, số hiệu, ngày và tên cơ quan với PDF gốc trước khi nghiệm thu.

Tool chỉ mở ở `localhost:8080`. Nếu cổng bận, dừng ứng dụng đang dùng cổng đó trước khi chạy lại. Trình duyệt trong Docker không thể tự mở Finder: khách mở `inbox/` bằng Finder. Không xóa `.local/` khi cập nhật.

## Bàn giao và cập nhật

Đưa khách [Hướng dẫn dùng hằng ngày](mac-user-guide.md), chỉ nơi đặt `inbox/`, cách mở và dừng bằng hai file `.command`, rồi xác nhận một tài liệu đã vào sổ. Nếu muốn quét mỗi 30 phút, bật lịch thư mục trong Cài đặt. Lịch chỉ chạy khi Mac và Docker Desktop đang hoạt động.

Khi cập nhật bằng ZIP: bấm `Dung-So-Ghi-Chep-Mac.command`; sao lưu `.local/` và `inbox/`; giải nén ZIP mới vào thư mục mới; chép hai thư mục dữ liệu sang đó; bấm file mở ở thư mục mới. Kiểm tra sổ cũ trước khi bỏ thư mục cũ. Không chạy hai bản cùng lúc. Không đưa `.local`, API key, token hoặc tài liệu khách vào gói phát hành.

Nếu Docker báo lỗi, mở Terminal tại thư mục tool và chạy `docker compose ps` hoặc `docker compose logs --tail=100 mailnotes`. Chỉ chia sẻ log đã che thông tin cá nhân. Bản Docker và bản `.app` có kho dữ liệu khác nhau; không đổi qua lại trong lúc bàn giao.
