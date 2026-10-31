# Cài Sổ ghi chép trên iMac

## Chọn đúng bản

- iMac Apple Silicon M1/M2/M3/M4: **SoGhiChep-macOS-AppleSilicon**.
- iMac Intel: **SoGhiChep-macOS-Intel**.

## Cài một lần

1. Tải artifact đúng chip, mở `SoGhiChep.dmg`, kéo `SoGhiChep.app` vào **Applications**.
2. Mở app. Nếu bản nội bộ chưa notarize bị macOS chặn, vào **System Settings → Privacy & Security**, kiểm tra đúng ứng dụng do đơn vị triển khai cung cấp rồi chọn mở. Không tắt Gatekeeper.
3. Tool tự mở trình duyệt tại localhost; lần đầu tạo mật khẩu quản trị từ 12 ký tự.
4. Trong Cài đặt, lưu GreenNode / VNG Cloud API key và cài tiện ích Chrome v0.9.1.
5. Nếu cần OCR PDF scan, quản trị viên cài Poppler bằng Homebrew (`brew install poppler`) trước khi mở app.

## Dùng và dữ liệu

- Dữ liệu nằm tại `~/Library/Application Support/SoGhiChep/`; thay app không xóa dữ liệu.
- PDF tải thủ công đặt tại `~/Downloads/So-Ghi-Chep-Inbox`.
- Nút **Mở thư mục** dùng Finder. Tiện ích có thể nhập trực tiếp đúng PDF Chrome vừa tải trong Downloads.
- Muốn dừng hẳn, dùng nút **Tắt tool**. Đóng tab không dừng lịch; máy ngủ hoặc tắt sẽ dừng lịch.

Trước bàn giao, thử một PDF chữ, một PDF scan và một Gmail có nhiều PDF trên chính tài khoản Chrome của khách. Bản CI không thay thế bước nghiệm thu này.
