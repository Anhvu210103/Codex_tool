# Kiểm thử 0.9.2 — 01/11/2026

## Các lỗi được tái hiện và sửa

- PDF trộn trang chữ/scan: giữ thứ tự trang, OCR riêng các trang thiếu chữ hoặc lỗi font. Một trang lỗi không xóa chữ đã lấy từ trang khác. Kết quả OCR bị cắt được báo rõ.
- Giới hạn OCR: tối đa 20 trang cần OCR trong 100 trang đầu, thời hạn tổng 180 giây; request không vượt thời gian còn lại. Giữ phần đã đọc khi có lỗi hoặc hết hạn.
- Thư mục nhiều PDF: đọc từng file, báo tệp trống/quá 20 MB, tiếp tục sau một file lỗi và thử lại file còn trong thư mục. Khi tắt app, hoàn tất file hiện tại và giữ các file chưa xử lý.
- Tên tệp: tránh tên dành riêng của Windows; tên quá dài vẫn chuyển được vào Da-xu-ly. Tải Markdown giữ tên tài liệu gốc.
- Xuất Markdown: sửa bản sao phân nhóm bị thiếu mà không gọi AI; manifest hỏng không làm dừng xử lý. Thêm tài liệu mới không ghi đè Markdown cũ. Tài liệu đã thành công vẫn có sổ khi tài liệu sau lỗi.
- Nội dung ngắn: tối đa 350 ký tự kể cả khi model trả quá dài, không phát sinh lượt gọi AI thứ hai chỉ để rút gọn.
- Tiện ích: sự kiện Chrome đến muộn sau khi Dừng không được khôi phục lượt cũ hoặc nhận nhầm vào lượt mới. Kiểm tra gồm cả Dừng rồi chạy lại.
- Giao diện: sửa thanh trên tràn ngang khi chọn chữ rất lớn trên màn hình hẹp. Tổng quan thể hiện lỗi quét thư mục và trạng thái xử lý PDF.

## Kiểm tra tự động

Chạy `bash scripts/release-check.sh` sau khi cài `requirements-build.txt` và Chromium của Playwright.

- 105 kiểm thử Python.
- Hai bộ kiểm tra Node: tải nhiều file, trạng thái lỗi, lịch tự động; và sự kiện tải đến muộn khi Dừng/chạy lại.
- Kiểm tra popup tiện ích và 12 tình huống chọn nút PDF bằng DOM giả lập.
- Trình duyệt Chromium với server Flask thật: tạo mật khẩu, đọc PDF, sửa nhóm, tải Markdown, tìm kiếm, lưu cỡ chữ, xóa, đăng xuất; kiểm tra bố cục 1366/1024/768/390 px với cỡ chữ rất lớn.
- Poppler được chạy thật trong phép thử PDF trộn trang; phản hồi OCR được giả lập để không gửi dữ liệu hoặc phát sinh phí API.
- GitHub Actions dựng và mở ứng dụng trên Windows x64, Linux x64, macOS Intel và macOS Apple Silicon; kiểm tra PDF → Markdown và nhập PDF tải từ Downloads.

Kiểm tra bổ sung: sửa nhóm khi đang quét trả thông báo bận ngay; xóa một tài liệu không ghi đè ghi chú Markdown của các tài liệu khác.

## Phạm vi cần nghiệm thu thật

Không có key GreenNode trong workspace kiểm thử này. Phân loại/OCR trong kiểm thử dùng phản hồi giả lập; chưa xác nhận model và hạn mức của tài khoản triển khai. Tài khoản Gmail thật và đúng máy khách vẫn cần nghiệm thu theo [GO-LIVE.md](GO-LIVE.md). Các phép thử tự động không chứng minh mọi thay đổi giao diện Gmail hoặc mọi PDF đều xử lý được.
