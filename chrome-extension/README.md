# Thử AI trên Gmail đã đăng nhập

1. Mở tool trên cùng máy, bật DeepSeek AI, lưu key và đồng ý gửi chữ tài liệu.
2. Cài đặt → Tiện ích Chrome → Tải tiện ích Chrome. Giải nén ZIP.
3. Mở `chrome://extensions`, bật Developer mode, chọn Load unpacked và thư mục có manifest.json.
4. Trong Cài đặt tool, tạo mã ghép nối. Bấm biểu tượng mảnh ghép Chrome → Sổ ghi chép — AI Gmail. Nhập địa chỉ tool đúng cổng và mã, bấm Lưu kết nối. Không nhập DeepSeek key vào tiện ích.
5. Mở Gmail bằng Chrome bình thường, đăng nhập thủ công. Tìm `has:attachment filename:pdf newer_than:7d`, rồi bấm Bắt đầu AI trong tiện ích.

Bản thử mở một hàng thư và chọn các nút PDF; tối đa 9 bước, hết hạn 3 phút. Chỉ các điều khiển đang thấy được đưa cho DeepSeek chọn. Không nhận ảnh chụp màn hình hoặc mật khẩu. Mở thư có thể đánh dấu đã đọc. Có nút Dừng; request AI đã gửi vẫn có thể tính phí. Chỉ tải một PDF mỗi lượt. Token các lượt chọn được ghi trong tool. Bộ lọc là danh sách Gmail bạn đang mở, không tự áp dụng bộ lọc Gmail API trong Cài đặt.

Trên Linux, tiện ích đợi Chrome tải xong và ưu tiên nhập đúng PDF vừa tải trong thư mục Downloads (kể cả đường dẫn XDG cấu hình). Tool không quét thư mục và không đọc file ngoài Downloads. Nếu không nhập local được, tiện ích thử đọc lại URL tải PDF và chuyển về tool. Nếu Google không cho đọc lại hoặc không xác định được tải xuống, dùng ô Chọn PDF trong tiện ích để ghi file đã tải vào sổ. Kiểm tra kết quả tại Sổ ghi chép → AI thao tác. PDF có chữ được chuyển thành Markdown rồi phân nhóm vào thư mục local; bản scan chuyển vào Cần xem lại, không chạy OCR.

Mã ghép nối được lưu trong bộ nhớ cục bộ của tiện ích, API key ở tool. Đổi mã trong tool để thu hồi quyền cũ. Bridge chỉ chấp nhận kết nối loopback từ extension có mã, không mở quyền cho website thông thường. Tiện ích cần quyền đọc Gmail, URL tệp đính kèm Google, tải xuống và kết nối localhost. Dùng thử trên một thư mẫu trước; chưa xác nhận Gmail thật hoặc iMac hoạt động cho tới khi thử trên máy người dùng. Không cần Playwright cho cách này.
