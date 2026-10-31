# Cài Sổ ghi chép trên Windows 10/11

## Cài một lần

1. Tải artifact **SoGhiChep-Windows-x86_64** từ GitHub Actions và giải nén toàn bộ ZIP vào một thư mục cố định.
2. Bấm đúp `SoGhiChep.exe`. Tool tự mở trình duyệt tại localhost; lần đầu tạo mật khẩu quản trị từ 12 ký tự.
3. Nếu SmartScreen cảnh báo, kiểm tra file đúng artifact do đơn vị triển khai cung cấp. Bản nội bộ chưa ký Microsoft code-signing có thể vẫn hiện cảnh báo.
4. Trong Cài đặt, lưu GreenNode / VNG Cloud API key và kiểm tra model. Cài cùng tiện ích Chrome v0.9.1 như hướng dẫn trong tool.
5. Nếu cần OCR PDF scan, quản trị viên cài Poppler cho Windows và bảo đảm lệnh `pdftoppm.exe` có trong PATH trước khi mở tool.

## Dùng và dữ liệu

- Bấm `SoGhiChep.exe` để mở. Bấm lần nữa chỉ mở lại trang đang chạy.
- Dữ liệu nằm tại `%LOCALAPPDATA%\SoGhiChep`; cập nhật EXE không xóa dữ liệu.
- PDF tải thủ công đặt tại `%USERPROFILE%\Downloads\So-Ghi-Chep-Inbox`.
- Nút **Mở thư mục** dùng File Explorer. Tiện ích có thể nhập trực tiếp đúng PDF Chrome vừa tải trong Downloads.
- Muốn dừng hẳn, dùng nút **Tắt tool** trong giao diện. Đóng tab trình duyệt không dừng lịch.

Trước bàn giao, thử một PDF chữ, một PDF scan và một Gmail có nhiều PDF. Kiểm tra file `.md`, nhóm, token/chi phí và lượt quét lại không tải trùng.
