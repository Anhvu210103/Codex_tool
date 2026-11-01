# Kiểm thử 0.9.3 — 01/11/2026

## Vòng đời tiện ích

Tái hiện và sửa các nhánh bất đồng bộ sau:

- Bấm Dừng khi Chrome đang kết nối debugger: lượt cũ không được gửi lệnh chạy sau khi người dùng đã dừng.
- Tắt lịch khi lượt tự động đang kết nối Chrome: lượt cũ bị hủy.
- Bật lịch chưa xong rồi tắt: bước bật cũ không được ghi đè lựa chọn tắt mới hơn.
- Bắt đầu lại ngay sau khi hủy một kết nối dở dang: Chrome được nhả kết nối trước khi nhận lượt mới.
- Dừng một lượt được khôi phục từ storage sau khi worker khởi động lại: phải nhả debugger, kể cả bản đồ sở hữu trong RAM chưa có lượt đó.
- Tắt lịch hoặc nhận sự kiện ngắt Chrome của lượt cũ trong lúc một lượt chạy tay mới bắt đầu: chỉ dừng đúng lượt đã yêu cầu.
- Dừng rồi chạy lại trên cùng tab Gmail khi còn phản hồi cũ đang chờ: mỗi lượt có mã riêng; phản hồi và lệnh Dừng cũ không được ghi trạng thái, nhận diện PDF hoặc kết thúc lượt mới. Content script mới có thể cài cạnh content script cũ trên tab đã mở mà không kích hoạt hai lượt song song.

Các lệnh debugger được xếp hàng và gắn với thế hệ lượt chạy. Các thay đổi lịch dùng thế hệ riêng để giữ lựa chọn cuối cùng của người dùng. Kiểm thử: `node tests/extension_lifecycle_race.cjs`.

`packaging/smoke_extension_sessions.py` thử trên DOM trong Chromium: giữ phản hồi khởi động hoặc trạng thái tải PDF, dừng và chạy lại, trả phản hồi cũ về muộn, gửi thêm lệnh Dừng cũ. Lượt mới vẫn ghi tài liệu và hoàn tất; lượt cũ không gửi tiếp lệnh.

## Kiểm tra tích hợp Chrome

`packaging/smoke_native_extension.py` dùng Chromium với tiện ích thật, API debugger/download/storage thật và server Flask thật. Trang Gmail và PDF là dữ liệu giả lập. Bài kiểm tra gồm 20 thư, 21 PDF (một thư có hai PDF), nhập từ Downloads, lưu 21 Markdown, quét lại không tải trùng, nhả debugger và xử lý đóng tab.

Chromium trong workspace chặn unpacked extensions bằng chính sách quản trị. Không sửa chính sách này; bài kiểm tra native được chạy trên GitHub Actions với Chromium do Playwright cung cấp. Không dùng tài khoản Gmail thật hoặc gọi GreenNode trong bài kiểm tra này.

Bộ kiểm thử Python và các phép thử giao diện của 0.9.2 tiếp tục được chạy. Kết quả native được xác nhận bằng lượt CI của bản chốt.

## Giới hạn thời gian chờ

Yêu cầu điều khiển từ tiện ích tới localhost có thời hạn 15 giây; chọn thao tác AI có 90 giây; nhập và xử lý PDF có 6 phút. Thời hạn bao gồm đọc thân phản hồi. Lỗi trả thông báo có thể xử lý và luôn giải phóng bộ hẹn giờ; không treo tiện ích vô hạn khi máy chủ ngừng trả dữ liệu.

Trang quản trị cũng có thời hạn 15 giây, riêng tải/đọc lại PDF là 6 phút. Thử lại, thông báo mất kết nối, dữ liệu nhóm dạng danh sách, header CSRF và upload multipart được kiểm tra. Luồng giao diện thật có thêm bước nạp nhóm mẫu.

Thanh công cụ PDF ưu tiên nút có nhãn, sau đó biểu tượng tải nằm giữa In và Thêm, cuối cùng mới dùng nút tải duy nhất ở bố cục khác. Ca có liên kết “Tải xuống” trong nội dung trang được tái hiện trước sửa và được thêm vào bộ 14 trường hợp DOM.

## Phục hồi và tải lớn

- Cache AI lỗi được thay bằng kết quả hợp lệ ở lần thử lại, không ghi một cache hit miễn phí giả. Phản hồi API sai cấu trúc vẫn được ghi usage đã trả về và không tạo ghi chép sai.
- Trạng thái đang chạy được ghi trước khi xử lý; khởi động lại nhận ra lượt gián đoạn. Lỗi tạo worker hoặc ghi trạng thái không làm giữ khóa xử lý.
- Lỗi HTTP bất ngờ trả mã tra cứu và ghi stack trace riêng trong errors.log.
- Khi tắt máy chủ, Gmail hoàn tất tài liệu hiện tại rồi ngừng lấy tài liệu tiếp theo.
- Thống kê chi phí đọc lịch sử từng dòng, không nạp snapshot giá và ID tài liệu vào RAM. Phép thử 12.000 dòng với snapshot 2 KB/dòng tái hiện mức cấp phát 33,3 MB trước sửa; bản mới đạt giới hạn dưới 10 MB và vẫn trả đúng 50 lượt gần nhất.
- Backend và tiện ích có phiên bản đối chiếu; báo cáo tiện ích ghi phiên bản tool đang kết nối. Phiên bản backend giữ nguyên cho tới khi khởi động lại, kể cả khi tệp giao diện trên đĩa đã cập nhật.
