---
name: so-ghi-chep-mac
description: Hỗ trợ khách cài đặt, sử dụng và xử lý lỗi Sổ ghi chép TCOM trên macOS bằng Docker Desktop; kiểm tra thư mục PDF, lịch quét, sổ ghi chép và Gmail khi được yêu cầu.
---

# Sổ ghi chép TCOM trên Mac

Dùng skill này khi người dùng trên iMac/MacBook muốn cài, mở, sử dụng, kiểm tra lịch quét, tìm PDF chưa vào sổ hoặc chuẩn bị thông tin lỗi để gửi người triển khai. Bản dành cho khách nằm trên nhánh `codex/mac-customer-test` và chạy bằng Docker Desktop. Ưu tiên trả lời tiếng Việt đơn giản, mỗi lần chỉ đưa bước khách cần làm tiếp theo.

## Nguồn thông tin của bản cài

- `HUONG-DAN-MAC.md`: trang bắt đầu.
- `deploy/mac-install.md`: cài một lần và bàn giao.
- `deploy/mac-user-guide.md`: thao tác hằng ngày.
- `compose.yml`, `Mo-So-Ghi-Chep-Mac.command`, `Dung-So-Ghi-Chep-Mac.command`: hành vi thực tế của gói Docker.
- `chrome-extension/worker.js` và `content.js`: chỉ đọc khi cần giải thích lịch Gmail hoặc báo cáo tiện ích.

Đọc các file hiện có trên máy trước khi hướng dẫn theo chi tiết phiên bản. Nếu khách dùng bản `.app` thay cho Docker, nói rõ đây là cách cài khác và đọc `packaging/README.md`; không suy ra đường dẫn `.local/` của Docker cho `.app`.

## Quy trình hỗ trợ

1. Xác định người dùng đang **cài lần đầu**, **dùng hằng ngày**, hay **gặp lỗi**. Nếu chưa rõ, kiểm tra các file có trong thư mục hiện tại và trạng thái Docker bằng thao tác chỉ đọc.
2. Cài lần đầu: hướng dẫn chọn Docker Desktop đúng chip; đặt toàn bộ ZIP vào một thư mục cố định; bấm đúp `Mo-So-Ghi-Chep-Mac.command`. File này tự mở Docker và trang web. Người dùng tự tạo mật khẩu quản trị, tự nhập DeepSeek API key và tích đồng ý rồi bấm **Lưu kết nối DeepSeek** trên trang **Cài đặt**. Không yêu cầu gửi key hoặc file cấu hình vào chat.
3. Dùng hằng ngày: khách chép PDF vào `inbox/` cạnh file mở, chờ file hoàn tất, bấm **Quét thư mục** trên **Tổng quan**, xem **Sổ ghi chép** (mặc định **Tất cả tài liệu**); có thể chọn riêng nguồn **Thư mục nhận PDF**. File thành công chuyển vào `inbox/Da-xu-ly`. Đóng tab khi dùng xong; lịch vẫn chạy khi Mac và Docker hoạt động. File `Dung-So-Ghi-Chep-Mac.command` chỉ dùng khi muốn dừng hẳn.
4. Nếu tài liệu chưa vào sổ, kiểm tra lần lượt: file có nằm trực tiếp trong `inbox/` không; đã tải/chép xong chưa; Docker có chạy không; lần quét cuối và lỗi trên Tổng quan; bộ lọc nguồn/ngày trong Sổ ghi chép; file có ở `Da-xu-ly` không. PDF trùng được bỏ qua theo nội dung. File lỗi ở lại để thử lại; không xóa file để “sửa” lỗi.
5. PDF scan: mục **Dùng OCR qua DeepSeek cho PDF scan** trong **Nội dung & chi phí** phải được bật và lưu, cùng với key và đồng ý gửi dữ liệu. Poppler đã có trong Docker. Luồng gửi ảnh từng trang cho DeepSeek, nhưng API/model có thể không nhận ảnh; khi thất bại, ghi rõ **Cần xem lại**. Không tuyên bố OCR thành công chỉ vì file được tải hoặc xuất hiện trong sổ. Luôn yêu cầu đối chiếu số hiệu, ngày tháng, tên cơ quan với PDF gốc.
6. Gmail tự động qua tiện ích: phạm vi mặc định là từ lần quét thành công gần nhất (lùi thêm một ngày), kiểm tra tối đa 20 trang kết quả, bỏ qua PDF đã ghi và kết thúc mỗi lượt; lịch tiếp tục sau 30 phút. Không khuyên dừng ngay khi gặp thư cũ vì thư cũ có thể còn PDF chưa xử lý. Nếu có lỗi hoặc chạm giới hạn, mốc thành công không tiến. Gmail API là kết nối khác, không trộn hai lịch.

## Kiểm tra kỹ thuật khi cần

Tại thư mục chứa `compose.yml`, dùng `docker compose ps` để xem trạng thái và `docker compose logs --tail=100 mailnotes` để tìm lỗi. Trước khi đưa log vào câu trả lời, loại bỏ địa chỉ email, tên tài liệu nhạy cảm, URL chứa token và mọi bí mật. `http://localhost:8080/health` chỉ cho biết web đang chạy, không chứng minh OCR hay phân loại đã thành công.

Trước khi cập nhật, sao lưu `.local/` và `inbox/`; dùng quy trình trong `deploy/mac-install.md`. Không dùng `docker compose down -v` hoặc xóa volume/thư mục dữ liệu. Đường dẫn `/app/.local/...` trong web là đường dẫn container; trên Mac tương ứng với `.local/...` trong thư mục tool. Không tự ý sửa dữ liệu SQLite, mật khẩu, key, mã ghép nối hoặc bật gửi tài liệu ra ngoài.

Nếu người dùng muốn Codex thao tác thay, chỉ thao tác trong phạm vi đã được họ cho phép; báo rõ khi một bước cần họ đăng nhập hoặc nhập bí mật trên máy. Nếu không có quyền truy cập máy Mac của khách, hướng dẫn thao tác cụ thể và chờ thông tin kết quả, không khẳng định đã chạy trên máy đó.
