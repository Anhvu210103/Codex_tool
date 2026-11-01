# Cài Sổ ghi chép trên iMac

## Chọn đúng bản

- Chip Apple M1/M2/M3/M4…: [Tải SoGhiChep-macOS-AppleSilicon.dmg](https://github.com/Anhvu210103/Codex_tool/releases/download/macos-v0.9.3/SoGhiChep-macOS-AppleSilicon.dmg).
- Bộ xử lý Intel: [Tải SoGhiChep-macOS-Intel.dmg](https://github.com/Anhvu210103/Codex_tool/releases/download/macos-v0.9.3/SoGhiChep-macOS-Intel.dmg).

Hai link tải trực tiếp không cần đăng nhập GitHub. Nếu chưa biết chip, mở menu ** → About This Mac**. [Trang tải dự phòng](https://github.com/Anhvu210103/Codex_tool/releases/tag/macos-v0.9.3): chọn đúng file `.dmg` trong **Assets**, không chọn **Source code**.

## Cài một lần

1. Tải file `.dmg` đúng chip rồi mở file. Nếu bản cũ đang chạy, bấm **Tắt tool** trước khi thay app. Kéo `SoGhiChep.app` vào **Applications**. Bản app này không cần cài Python hoặc Docker.
2. Mở app. Nếu bản nội bộ chưa notarize bị macOS chặn, vào **System Settings → Privacy & Security**, kiểm tra đúng ứng dụng do đơn vị triển khai cung cấp rồi chọn mở. Không tắt Gatekeeper.
3. Tool tự mở trình duyệt tại localhost; lần đầu tạo mật khẩu quản trị từ 12 ký tự.
4. Trong Cài đặt, lưu GreenNode / VNG Cloud API key và cài tiện ích Chrome v0.9.3.
5. Nếu cần OCR PDF scan, quản trị viên cài Poppler bằng Homebrew (`brew install poppler`) trước khi mở app. App tự tìm Poppler ở thư mục Homebrew của Mac Intel và Apple Silicon, kể cả khi mở bằng Finder.

## Dùng và dữ liệu

- Dữ liệu nằm tại `~/Library/Application Support/SoGhiChep/`; thay app không xóa dữ liệu.
- PDF tải thủ công đặt tại `~/Downloads/So-Ghi-Chep-Inbox`.
- Nút **Mở thư mục** dùng Finder. Tiện ích có thể nhập trực tiếp đúng PDF Chrome vừa tải trong Downloads.
- Muốn dừng hẳn, dùng nút **Tắt tool**. Đóng tab không dừng lịch; máy ngủ hoặc tắt sẽ dừng lịch.

Trước bàn giao, thử một PDF chữ, một PDF scan và một Gmail có nhiều PDF trên chính tài khoản Chrome của khách. Bản CI không thay thế bước nghiệm thu này.
