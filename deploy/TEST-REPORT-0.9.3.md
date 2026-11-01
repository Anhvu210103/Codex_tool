# Kiểm thử 0.9.3 — 01/11/2026

## Vòng đời tiện ích

Tái hiện và sửa các nhánh bất đồng bộ sau:

- Bấm Dừng khi Chrome đang kết nối debugger: lượt cũ không được gửi lệnh chạy sau khi người dùng đã dừng.
- Tắt lịch khi lượt tự động đang kết nối Chrome: lượt cũ bị hủy.
- Bật lịch chưa xong rồi tắt: bước bật cũ không được ghi đè lựa chọn tắt mới hơn.
- Bắt đầu lại ngay sau khi hủy một kết nối dở dang: Chrome được nhả kết nối trước khi nhận lượt mới.
- Dừng một lượt được khôi phục từ storage sau khi worker khởi động lại: phải nhả debugger, kể cả bản đồ sở hữu trong RAM chưa có lượt đó.

Các lệnh debugger được xếp hàng và gắn với thế hệ lượt chạy. Các thay đổi lịch dùng thế hệ riêng để giữ lựa chọn cuối cùng của người dùng. Kiểm thử: `node tests/extension_lifecycle_race.cjs`.

## Kiểm tra tích hợp Chrome

`packaging/smoke_native_extension.py` dùng Chromium với tiện ích thật, API debugger/download/storage thật và server Flask thật. Trang Gmail và hai PDF là dữ liệu giả lập. Bài kiểm tra gồm tải hai PDF, nhập từ Downloads, lưu Markdown, quét lại không tải trùng, nhả debugger và xử lý đóng tab.

Chromium trong workspace chặn unpacked extensions bằng chính sách quản trị. Không sửa chính sách này; bài kiểm tra native được chạy trên GitHub Actions với Chromium do Playwright cung cấp. Không dùng tài khoản Gmail thật hoặc gọi GreenNode trong bài kiểm tra này.

Bộ kiểm thử Python và các phép thử giao diện của 0.9.2 tiếp tục được chạy. Kết quả native được xác nhận bằng lượt CI của bản chốt.
