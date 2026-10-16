# Thử AI trên Gmail đã đăng nhập

1. Mở tool trên cùng máy, bật DeepSeek AI, lưu key và đồng ý gửi chữ tài liệu.
2. Cài đặt → Tiện ích Chrome → Tải tiện ích Chrome. Giải nén ZIP.
3. Mở `chrome://extensions`, bật Developer mode, chọn Load unpacked và thư mục có manifest.json.
4. Trong Cài đặt tool, tạo mã ghép nối. Bấm biểu tượng mảnh ghép Chrome → Sổ ghi chép — AI Gmail. Nhập địa chỉ tool đúng cổng và mã, bấm Lưu kết nối. Không nhập DeepSeek key vào tiện ích.
5. Mở Gmail bằng Chrome bình thường, đăng nhập thủ công. Tìm `has:attachment filename:pdf newer_than:7d`, rồi bấm Xử lý tối đa 20 thư đang hiện trong tiện ích.

Tiện ích đọc danh sách thư đang hiển thị trong Gmail và thao tác lần lượt tối đa 20 thư. Mỗi thư được mở, liệt kê tất cả ô PDF, mở từng PDF, bấm Tải xuống, đợi Chrome xác nhận tải xong và tool lưu/phân loại xong rồi mới sang file kế tiếp. Có nút Thử 1 thư và Dừng. Không gửi, xóa hay sửa nội dung thư; mở thư có thể đánh dấu đã đọc. DeepSeek chỉ dùng khi tool phân loại/tóm tắt PDF, không dùng để chọn lại nút trên Gmail. Nếu cùng PDF đã có trong sổ, tool bỏ qua để tránh tốn token. Bộ lọc là danh sách Gmail bạn đang mở; bộ lọc Gmail API trong Cài đặt không được áp dụng ở đây.

Lượt quét xử lý tối đa 20 hàng thư hiện có trong trang Gmail, kể cả khi phải cuộn để thấy hết. Gmail có thể chỉ nạp một phần hàng trong DOM hoặc thay đổi giao diện; tool sẽ báo lỗi nếu không tìm lại được thư, PDF, nút tải hay nút quay lại. Tiến độ cuối cùng ghi số thư, PDF đã lưu và lỗi. Mở lại cùng danh sách sẽ bỏ qua các PDF đã có; không tự động thử lại tài liệu scan bằng OCR.

Trên Linux, tiện ích đợi Chrome tải xong và ưu tiên nhập đúng PDF vừa tải trong thư mục Downloads (kể cả đường dẫn XDG cấu hình). Tool không quét thư mục và không đọc file ngoài Downloads. Nếu không nhập local được, tiện ích thử đọc lại URL tải PDF và chuyển về tool. Nếu Google không cho đọc lại hoặc không xác định được tải xuống, dùng ô Chọn PDF trong tiện ích để ghi file đã tải vào sổ. Kiểm tra kết quả tại Sổ ghi chép → AI thao tác. PDF có chữ được chuyển thành Markdown rồi phân nhóm vào thư mục local; bản scan chuyển vào Cần xem lại, không chạy OCR.

Mã ghép nối được lưu trong bộ nhớ cục bộ của tiện ích, API key ở tool. Đổi mã trong tool để thu hồi quyền cũ. Bridge chỉ chấp nhận kết nối loopback từ extension có mã, không mở quyền cho website thông thường. Tiện ích cần quyền đọc Gmail, URL tệp đính kèm Google, tải xuống và kết nối localhost. Dùng nút Thử 1 thư để kiểm tra trước; chưa xác nhận Gmail thật hoặc iMac hoạt động cho tới khi thử trên máy người dùng. Không cần Playwright cho cách này.
