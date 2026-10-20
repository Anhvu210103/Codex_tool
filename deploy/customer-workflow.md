# Quy trình dùng Sổ ghi chép cho khách hàng

## Những việc dùng hằng ngày

1. **Nhận tài liệu.** Nếu không tự lấy được trên website, tải mọi PDF vào thư mục hiển thị ở **Cài đặt → Thư mục nhận PDF thủ công**. Trên **Tổng quan**, bấm **Thư mục PDF** để xem nơi đặt file và **Quét thư mục** để xử lý ngay. Trên Docker Mac/Windows, thư mục này là `inbox` cạnh file mở tool; trình duyệt không thể tự mở Finder/File Explorer của máy khách. Có thể bật tự quét theo chu kỳ đã lưu. PDF xong được chuyển vào `Da-xu-ly`; file lỗi ở lại để xử lý tiếp.
2. **Xem kết quả.** Ở **Tổng quan**, xem tài liệu mới, tài liệu cần kiểm tra và tiền AI ước tính. Mở **Sổ ghi chép**, chọn nguồn **Thư mục nhận PDF**, **PDF tải lên**, **Gmail qua tiện ích** hoặc **Gmail API**. Mỗi tài liệu có nội dung ngắn, nhóm và đường dẫn lưu trên máy.
3. **Sửa phân loại.** Mở tài liệu cần xem lại và bấm **Sửa nhóm**. Thao tác này cập nhật sổ mà không gọi AI lại. Chỉnh danh sách/mô tả nhóm ở **Nhóm tài liệu** để áp dụng cho tài liệu xử lý sau đó.

## Thiết lập một lần

- Lưu **DeepSeek API key** và xác nhận đồng ý gửi nội dung tài liệu cho DeepSeek. AI dùng một lượt để phân nhóm và tóm tắt. Số tiền trong tool là ước tính, không phải hóa đơn.
- Chọn chu kỳ kiểm tra ở mục **Thư mục nhận PDF thủ công**, bật tự quét nếu cần. Lịch chỉ chạy khi tool và máy đang hoạt động.
- Với PDF scan không có lớp chữ, cấu hình **OCR cloud** nếu muốn tool đọc được ảnh. Bản này có thể gửi ảnh từng trang qua DeepSeek OCR để trích chữ rồi phân nhóm; không thể biến PDF scan thành chữ chỉ bằng đổi sang Markdown. OCR có thể phát sinh thêm phí AI.
- Nếu muốn tự lấy Gmail, chọn **một** trong hai cách: tiện ích Chrome thao tác trên Gmail đang đăng nhập, hoặc Gmail API qua Google OAuth. Hai cách có lịch và cách kết nối khác nhau. Thử một thư có nhiều PDF trước khi bật lịch.

## Giao diện đã tinh gọn

- **Giữ trên trang chính:** thao tác thư mục PDF, PDF tải lên, ghi chép gần nhất, tài liệu cần xem lại, tiền/token AI và sửa nhóm.
- **Đưa vào mục mở khi cần:** Gmail API, tiện ích Chrome, OCR cloud, tùy chỉnh model/giới hạn chữ/đơn giá, đổi mật khẩu và cập nhật tool.
- **Bỏ khỏi luồng khách:** nút dữ liệu mẫu và lựa chọn trích đoạn miễn phí. Mã kiểm thử cũ còn trong repository để kiểm tra tương thích dữ liệu, nhưng tài liệu mới mặc định dùng DeepSeek khi đã có key và sự đồng ý.

Nếu trang Gmail/website không tải được PDF, luồng thư mục vẫn hoạt động độc lập. Tool chống trùng theo nội dung file; khi một file lỗi, giữ lại file và báo trạng thái để người dùng thử lại. Không xóa dữ liệu trong `.local` khi cập nhật.
