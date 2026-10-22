# Rà soát bản Mac trước khi cài khách — 21/10/2026

Phạm vi là nhánh `codex/mac-customer-test`, chạy Docker Desktop trên Mac, dùng chung backend với bộ mã nguồn trong nhánh này. Đã sửa các vấn đề phát hiện được; chưa thay việc nghiệm thu trên iMac thật.

## Những việc đã sửa

- Chữ mặc định 20px trên trình duyệt mới, có tùy chọn 22px; thêm hiện mật khẩu, tên nút tiếng Việt và trạng thái chưa lưu cài đặt.
- Tổng quan và Sổ mặc định **Tất cả tài liệu**, gộp các nguồn thật; dữ liệu mẫu cũ không lẫn vào. Bộ lọc có nút xóa, thứ tự tài liệu tính theo thời gian thực khi dữ liệu có múi giờ khác nhau.
- Bảng sổ còn bốn cột chính; tóm tắt rộng hơn, file tải/nơi lưu nằm dưới từng tên tài liệu. Phần nhập PDF thu lại sau khi xử lý xong. Đổi trang trở về đầu trang; lượt cập nhật nền không đóng chi tiết đang mở.
- Lưu kết nối DeepSeek gộp lưu key và cài đặt sau khi khách đã tích đồng ý. OCR nằm cùng cài đặt AI. Kết quả OCR bị cắt không được coi là đọc xong.
- Tổng quan phản ánh cả đọc PDF trực tiếp và quét thư mục: đang đọc file nào, số mới/đã có/cần xem lại và lỗi. Nút quét không nhận thêm lượt trong lúc đang xử lý.
- Quét thư mục giữ lần lượt từng PDF thay vì nạp toàn bộ file vào RAM. File quá 20 MB có lỗi rõ; file chưa tải xong được chờ.
- Launcher Mac truyền đường dẫn host cho giao diện, giữ đường dẫn lưu nội bộ cho tải file. Bản Docker không hiển thị nút cập nhật chỉ dành cho bản native.
- `inbox/` và dữ liệu local lồng nhau được loại khỏi Git/Docker build context, tránh đưa tài liệu khách vào image khi dựng lại.

## Bằng chứng kiểm tra

| Kiểm tra | Kết quả |
| --- | --- |
| Python unit/integration | 80 kiểm thử đạt: đăng nhập, quyền/CSRF, PDF, Markdown, nhóm, chi phí, folder, tất cả nguồn, xuất sổ và lỗi OCR |
| JavaScript, shell launcher, Compose | Kiểm tra cú pháp/cấu hình đạt |
| Chromium thật | Tạo mật khẩu, hiện mật khẩu, lưu AI, upload PDF thật, quét folder, sửa nhóm, tìm/xóa lọc, tải sổ theo ngày và giữ chi tiết qua lượt polling; không lỗi JS/HTTP |
| Bố cục | 1920, 1440, 1366, 1024, 390px; cuộn ngang chỉ nằm trong bảng trên cửa sổ hẹp |
| Docker trên Linux | Tạo mật khẩu, Poppler, nhập folder, ghi Cần xem lại cho scan chưa OCR, chống trùng và giữ sổ/mật khẩu sau restart đạt |

Các lượt phân nhóm trong thử trình duyệt dùng DeepSeek giả lập và dữ liệu tạm, không dùng key hay tài liệu khách. Lệnh kiểm tra có thể chạy lại: `python -m unittest discover -s tests -q` và `python packaging/smoke_customer_ui.py --screenshots /tmp/customer-ui` (cần Playwright/Chromium).

Lượt Docker build ban đầu vướng CA của proxy môi trường phát triển; bản test dựng được bằng cách truyền CA tin cậy của môi trường qua build secret. Không tắt kiểm tra TLS và không đưa CA riêng này vào bộ cài khách.

## Những gì cần xác nhận tại máy khách

- Bấm mở bằng Finder, Docker Desktop, quyền thư mục và khả năng chạy trên đúng chip/macOS của iMac.
- Chất lượng phân nhóm/tóm tắt và usage với DeepSeek API thật.
- API/model DeepSeek của khách có thật sự nhận ảnh để OCR scan hay không; hiện chưa có bằng chứng live API trong lần rà soát này. Base64 chỉ mã hóa ảnh, không tự cung cấp khả năng đọc ảnh cho model.
- Gmail thật, nhiều tệp PDF/thư và lịch tiện ích nếu nằm trong phạm vi bàn giao. Khả năng tự thao tác website nhà nước khác vẫn cần bộ kết nối/kiểm thử riêng.

Làm theo [kiểm tra bàn giao Mac](mac-handover-check.md), dùng luồng thư mục làm đường vận hành chính nếu nguồn web chưa ổn.

## Tiện ích Gmail 0.8.0 — cập nhật 22/10/2026

Trạng thái và phiên bản nằm trên cùng. Ghép nối thu lại sau khi lưu; phần quét tay nằm cao để dễ bấm. Khi đang chạy, phần quét tay được ẩn và nút Dừng lượt này hiện rõ. Tắt lịch 30 phút là thao tác riêng. Chọn thời gian mới không ngắt lượt cũ; báo cáo đầy đủ và nhập PDF thủ công nằm trong phần mở khi cần.

Đã kiểm tra popup với Chromium và API Chrome mô phỏng: ghép nối, từ chối địa chỉ ngoài localhost, khoảng ngày sai/đúng, lưu phạm vi không dừng lượt đang chạy, bật/tắt lịch, dừng lượt, báo lỗi, sao chép báo cáo có phiên bản nhưng không kèm mã ghép nối, nhập PDF thủ công và bố cục 440/390/360px. Có thể chạy lại bằng `python packaging/smoke_extension_ui.py --screenshots /tmp/extension-ui`.

Đã bổ sung kiểm thử lịch tự động: khi lưu kết nối thất bại, lịch phải giữ trạng thái tắt, không tạo báo thức hay bắt đầu quét. Khi lưu thành công mới bật lịch và chạy ngay lượt đầu.

Chính sách Chromium trong môi trường phát triển chặn tiện ích ngoài, nên lần kiểm tra này không nạp được extension thật và không quét Gmail thật. Bộ kiểm thử Python đạt 81 kiểm thử trên nhánh Mac. Cần nghiệm thu tiện ích 0.8.0 trên Chrome của khách theo phần Gmail trong tài liệu bàn giao.
