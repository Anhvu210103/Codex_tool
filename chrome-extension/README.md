# Tiện ích Sổ ghi chép Gmail — 0.8.6

Tiện ích tự bấm trên Gmail đang đăng nhập trong Chrome để tải PDF vào Sổ ghi chép. Giao diện dùng chữ 18px, nút tối thiểu 50px, trạng thái nằm đầu cửa sổ. Phiên bản luôn hiện ở đầu để kiểm tra đã nạp đúng bản mới.

## Kết nối một lần

1. Mở Sổ ghi chép trên máy và đăng nhập. Vào **Cài đặt → Tiện ích Chrome → Tạo mã ghép nối**.
2. Bấm biểu tượng mảnh ghép của Chrome rồi mở **Sổ ghi chép — AI Gmail**. Mục **Kết nối lần đầu** tự mở khi chưa có mã.
3. Kiểm tra **Địa chỉ Sổ ghi chép** khớp trang đang mở, dán mã vào ô **Mã ghép nối**, bấm **Lưu kết nối**. Khi thành công mục này tự thu lại. Không gửi mã vào chat.

## Dùng hằng ngày

- **Thử 1 thư:** mở danh sách thư có PDF trong Gmail, bấm nút này để kiểm tra một thư trước. Kết quả được ghi vào Sổ ghi chép trên máy.
- **Quét 20 thư:** xử lý tối đa 20 hàng thư trong danh sách Gmail đang mở. Các nút chạy này dùng danh sách trên màn hình, không tự áp dụng phạm vi thời gian của lịch tự động.
- **Kiểm tra mỗi 30 phút:** bật một lần. Tiện ích quét ngay, rồi mỗi 30 phút kiểm tra lượt mới. Mỗi lượt xong tự dừng; file đã lưu được bỏ qua. Chrome, phiên Gmail và Sổ ghi chép cần đang chạy. Đóng cửa sổ tiện ích không dừng lượt.
- **Dừng lượt này:** chỉ hiện khi đang chạy. Nếu lịch 30 phút còn bật, lượt sau vẫn được chạy; muốn ngừng cả lịch thì bỏ tích **Kiểm tra mỗi 30 phút**.

Trong mục **Thư cần kiểm tra**, mặc định là **Thư mới từ lần trước**: lấy mốc lần quét thành công gần nhất và lùi thêm một ngày để tránh sót. Có thể đổi sang hôm nay, 7 ngày, khoảng ngày hoặc tất cả thư PDF. Bấm **Lưu phạm vi cho lượt sau**; thao tác này không dừng lượt đang chạy. Tất cả thư có thể lâu: mỗi lượt tự động tối đa 20 trang, mỗi trang tối đa 100 hàng thư. Lượt có lỗi hoặc chạm giới hạn không tiến mốc thành công.

Trạng thái đầu cửa sổ tóm tắt lượt đang chạy. Thông báo đầy đủ và log kỹ thuật nằm trong **Báo cáo và hỗ trợ**, có nút **Sao chép báo cáo**. Báo cáo kèm phiên bản, phạm vi và trạng thái để người hỗ trợ kiểm tra. Nếu có lỗi, nút **Thử lại mục chưa xong** hiện ra; mở lại danh sách thư cũ trước khi bấm. **Đưa PDF đã tải vào sổ** là cách xử lý thủ công khi file đã về máy nhưng chưa tự vào sổ.

## Cập nhật bản đã cài

Tải ZIP tiện ích mới trong Cài đặt của tool, giải nén vào thư mục cố định. Mở `chrome://extensions`, nạp đúng thư mục có `manifest.json` hoặc thay nội dung thư mục Chrome đang dùng rồi bấm **Reload**. Đầu popup phải hiện **v0.8.6**. Chỉ Reload một thư mục cũ trong Downloads không tải mã mới. Không cần tạo mã ghép nối lại nếu vẫn dùng cùng tiện ích và cùng tool; khi nạp thành một tiện ích mới thì ghép nối lại.

## Cơ chế và giới hạn

Mỗi thư được mở để liệt kê mọi PDF. Tiện ích mở lần lượt từng PDF, bấm nút tải của trình xem, chờ Chrome tải xong và tool nhập xong rồi mới chuyển file tiếp theo. PDF đã ghi nhớ không tải lại; các thư khác nhau chứa cùng PDF có thể phải tải để tool kiểm tra mã băm trước khi bỏ qua. Một thư có nhiều PDF được xử lý từng file. Mở thư có thể đánh dấu đã đọc; tiện ích không gửi hoặc xóa email.

Tiện ích kiểm tra lại thư cũ trong phạm vi để không bỏ sót PDF mới, không dừng ngay khi gặp thư đã có. Thao tác dựa vào các nút và nội dung trang Gmail, không dùng DeepSeek để chọn nút; DeepSeek được dùng ở tool khi đọc/phân nhóm/tóm tắt tài liệu. Gmail thay đổi giao diện hoặc phiên đăng nhập hết hạn có thể làm thao tác lỗi. Khi không tiếp tục an toàn được, tiện ích báo lỗi; không coi file đã tải là đã vào sổ.

Khi file đã về máy mà không tự nhập, chọn PDF tại tiện ích hoặc đưa vào `inbox` của tool. PDF scan chỉ được thử OCR theo cấu hình DeepSeek của tool; cần đối chiếu bản gốc và xác minh API nhận ảnh. Gmail API trong trang Cài đặt là kết nối khác, có lịch riêng.

Mã ghép nối lưu trong vùng cục bộ của tiện ích; API key lưu tại tool. Bridge chỉ nhận kết nối localhost được ghép nối. Quyền Chrome debugger dùng để gửi thao tác chuột/phím vào tab đang quét. Kiểm thử UI với Chromium không thay thế nghiệm thu Gmail thật và nhiều PDF trên máy khách.

Bản 0.8.1 cố định chiều rộng popup 440px, sửa lỗi cửa sổ Chrome bị co hẹp khiến chữ xuống dòng liên tục. Các thao tác quét và lịch tự động nằm phía trên; báo cáo, kết nối và nhập file nằm dưới.

Bản 0.8.2 sửa nhận diện nút tải PDF: không buộc nút vào tọa độ sát mép phải, đọc nhãn trên biểu tượng con, bỏ nút bị che/chưa bật và chờ tối đa 12 giây. Nếu không chọn được, báo cáo có các dòng `chan-doan-tai`, `nut-tai-bi-loai` hoặc `toolbar-pdf`. Không bấm khi có nhiều nút tải chưa phân biệt được. Kiểm thử DOM: `python packaging/smoke_extension_download.py` (cần Playwright/Chromium; không thay kiểm thử Gmail thật).

Bản 0.8.3 sửa lỗi biến chưa được định nghĩa trong nhánh xử lý PDF của 0.8.2. Kiểm thử luồng `mở thư → mở PDF → chọn nút tải → ghi kết quả → đóng trình xem` có thể chạy bằng `python -m unittest tests.test_extension_scan_flow`.

Bản 0.8.4 ưu tiên đúng nút Đóng của trình xem và khôi phục trực tiếp bộ lọc Gmail đã mở khi nút Đóng hoặc phím Esc không phản hồi.

Bản 0.8.5 ưu tiên nút tải ngay trên từng thẻ PDF trong email. Trình xem PDF chỉ được mở làm phương án dự phòng, tránh trạng thái toolbar chưa sẵn sàng hoặc lớp tải của Gmail che file tiếp theo.

Bản 0.8.6 tự mở lại đúng email đang xử lý khi Gmail không đóng trình xem bằng nút Đóng hoặc phím Esc. Nhờ vậy email có nhiều PDF tiếp tục từ file kế tiếp và chỉ quay lại danh sách sau khi xử lý xong email.
