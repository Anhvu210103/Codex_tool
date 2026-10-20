# Sổ ghi chép tài liệu · Powered by TCOM

Tool nhận PDF từ thư mục trên máy, file tải lên hoặc Gmail; trích chữ, dùng DeepSeek phân nhóm và viết nội dung ngắn, rồi lưu vào sổ ghi chép. Một tài liệu có thể thuộc nhiều nhóm. Những file chưa đọc được chữ hoặc chưa rõ nhóm được đánh dấu để xem lại. [Quy trình dùng cho khách hàng](deploy/customer-workflow.md) ghi rõ các bước hằng ngày và phần chỉ cần thiết lập một lần.

## Dùng trên Linux

Mở `Mo-So-Ghi-Chep.sh` trong thư mục đã cài `.venv`. Tool mở trang quản trị trên máy này; lần đầu tạo mật khẩu quản trị. Đóng tab chỉ đóng giao diện, còn lịch tự động tiếp tục khi tool chạy. Dùng nút **Tắt tool** trong giao diện để dừng hẳn. Nếu cổng 8080 đang bận, tool có thể chọn cổng 8081–8090 và mở địa chỉ mới.

Trong **Cài đặt**, lưu DeepSeek API key và xác nhận đồng ý gửi nội dung tài liệu. Xem lại **Nhóm tài liệu**. Để thử luồng ổn định nhất, trên **Tổng quan** bấm **Mở thư mục PDF**, chép một PDF có chữ vào đó rồi bấm **Quét thư mục**. Mở **Sổ ghi chép → Thư mục nhận PDF** để xem kết quả. Sau đó bật **Tự quét thư mục** với chu kỳ phù hợp. PDF đã xử lý được chuyển vào `Da-xu-ly`; PDF lỗi ở lại để thử lại. Có thể tải PDF trực tiếp ở Sổ ghi chép khi chỉ muốn thử một file.

PDF scan cần Poppler (`pdftoppm`) trên máy để chuyển trang thành ảnh trước khi thử gửi DeepSeek OCR. Trên Ubuntu/Debian cài `sudo apt install poppler-utils`; trên Mac cài `brew install poppler`. Bản này thử OCR từng trang ảnh qua DeepSeek; nếu API không nhận ảnh hoặc OCR thất bại, file scan được giữ ở nhóm **Cần xem lại**. Mục **Token & chi phí** hiển thị số đo API và tiền ước tính, không thay thế hóa đơn DeepSeek.

## Gmail và website

Tiện ích Chrome thao tác trên Gmail đang đăng nhập; Gmail API là kết nối riêng qua Google OAuth. Cả hai chỉ là **nguồn lấy tài liệu**. Hãy thử một thư và kiểm tra sổ trước khi bật lịch. Tự thao tác trên website khác cần kiểm tra giao diện, quyền truy cập và quy trình tải riêng; nếu chưa làm được, dùng thư mục PDF để khách vẫn có thể làm việc. Xem [hướng dẫn nguồn và triển khai](deploy/README.md) và [quy trình Linux/macOS](deploy/linux-macos.md).

## Dữ liệu và cập nhật

Dữ liệu, cấu hình, key và sổ của bản chạy từ mã nguồn nằm trong `.local/` của thư mục tool. Không gửi `.local`, `.env`, token, OAuth JSON hoặc API key cho người hỗ trợ. Để cập nhật bản Linux chạy bằng `.sh`, vào **Cài đặt → Cập nhật tool**, chờ mở lại rồi tải lại trang bằng Ctrl+Shift+R. Bản cập nhật giữ nguyên `.local` và `.venv`. Nếu đang dùng app đóng gói, cần thay bản app thay vì bấm cập nhật mã nguồn.

Thông tin build app ở [packaging/README.md](packaging/README.md). Nhà phát triển có thể chạy `python3 -m venv .venv`, cài `requirements-web.txt`, rồi kiểm tra bằng `.venv/bin/python -m unittest discover -s tests -v`. Không cần DeepSeek key để chạy bộ test; các lượt AI trong test được giả lập.
