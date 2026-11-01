# Cài Sổ ghi chép trên Windows 10/11

## Cài một lần

1. Bấm [Tải Sổ ghi chép Windows 0.9.3](https://github.com/Anhvu210103/Codex_tool/releases/download/windows-v0.9.3/SoGhiChep-Windows-x86_64.zip) để tải ZIP trực tiếp, không cần tài khoản GitHub. Có thể mở [trang phát hành](https://github.com/Anhvu210103/Codex_tool/releases/tag/windows-v0.9.3) rồi bấm `SoGhiChep-Windows-x86_64.zip` trong **Assets**. Đừng chọn **Source code**.
2. Mở **Downloads**, chuột phải file ZIP vừa tải → **Extract All… / Giải nén tất cả** → **Extract**. Mở thư mục vừa giải nén, bên trong có `SoGhiChep.exe` và `HUONG-DAN.txt`.
3. Nếu bản cũ đang chạy, bấm **Tắt tool** trong giao diện trước. Bấm đúp `SoGhiChep.exe` mới. Tool tự mở trình duyệt tại localhost; lần đầu tạo mật khẩu quản trị từ 12 ký tự. Không cần cài Python hoặc Docker để mở bản EXE.
4. Nếu SmartScreen cảnh báo, kiểm tra file đúng gói phát hành do đơn vị triển khai cung cấp. Bản nội bộ chưa ký Microsoft code-signing có thể vẫn hiện cảnh báo.
5. Trong Cài đặt, lưu GreenNode / VNG Cloud API key và kiểm tra model. Cài cùng tiện ích Chrome v0.9.3 như hướng dẫn trong tool.
6. Nếu cần OCR PDF scan, quản trị viên cài Poppler cho Windows và bảo đảm lệnh `pdftoppm.exe` có trong PATH trước khi mở tool.

## Dùng và dữ liệu

- Bấm `SoGhiChep.exe` để mở. Bấm lần nữa chỉ mở lại trang đang chạy.
- Dữ liệu nằm tại `%LOCALAPPDATA%\SoGhiChep`; cập nhật EXE không xóa dữ liệu.
- PDF tải thủ công đặt tại `%USERPROFILE%\Downloads\So-Ghi-Chep-Inbox`.
- Nút **Mở thư mục** dùng File Explorer. Tiện ích có thể nhập trực tiếp đúng PDF Chrome vừa tải trong Downloads.
- Muốn dừng hẳn, dùng nút **Tắt tool** trong giao diện. Đóng tab trình duyệt không dừng lịch.

Trước bàn giao, thử một PDF chữ, một PDF scan và một Gmail có nhiều PDF. Kiểm tra file `.md`, nhóm, token/chi phí và lượt quét lại không tải trùng.
