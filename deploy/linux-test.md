# Nghiệm thu Linux trước khi bàn giao

Phạm vi bản 0.9.1: chạy tay tối đa 20 thư mỗi lượt. Lịch tiện ích chạy ngay khi bật rồi kiểm tra mỗi 30 phút, tối đa 100 thư mỗi trang và 20 trang mỗi lượt. Mỗi PDF được chuyển thành Markdown, GreenNode / VNG Cloud phân nhóm và tóm tắt, sau đó bản `.md` được lưu theo nhóm. Gmail API là một nguồn riêng, không dùng chung lịch với tiện ích.

## Kiểm tra một lần trên máy khách

1. Mở tool và Chrome. Trong Cài đặt, lưu GreenNode / VNG Cloud API key, kiểm tra model `deepseek/deepseek-v4.1-flash-thirdparty` và danh sách nhóm.
2. Cài tiện ích đúng bản **0.9.1**, ghép nối với đúng địa chỉ localhost của tool. Sau mỗi lần cập nhật, bấm Reload tại `chrome://extensions` và tải lại Gmail.
3. Mở danh sách Gmail có một thư chứa ít nhất hai PDF. Bấm **Thử 1 thư**. Không bấm hỗ trợ trong lúc chạy.
4. Báo cáo phải có `bam-tai-truc-tiep` hoặc `tim-nut-tai`, tiếp theo là `chrome-bat-dau`, `chrome-xong` và `da-luu` cho từng file. Một file lỗi phải được bỏ qua để file sau vẫn chạy.
5. Trong **Sổ ghi chép → AI thao tác**, kiểm tra tiêu đề, nội dung ngắn, nhóm và đường dẫn `.md`. Thư mục `Theo-nhom/` chỉ chứa Markdown đã phân loại; `Can-xem-lai/` chứa Markdown cần kiểm tra. PDF nguồn nằm trong vùng dữ liệu nội bộ để tool đọc lại và không được hiển thị làm đường dẫn kết quả.
6. Sửa nhóm trong sổ. File Markdown phải chuyển đúng nhóm mà không phát sinh lượt AI. Đọc lại cùng PDF không tạo dòng trùng khi nội dung và cấu hình không đổi.
7. Thử một PDF scan. Nếu model nhận ảnh, nội dung OCR phải được đánh dấu cần đối chiếu bản gốc. Nếu model không nhận ảnh, tài liệu phải vào **Cần xem lại** với lý do rõ ràng; không được tạo file Markdown 0 byte.
8. Bấm **Quét 20 thư**. Lượt phải đi hết danh sách dù có file lỗi. Báo cáo cuối lượt phải tách số PDF mới, PDF đã có và lỗi. Bấm **Thử lại mục chưa xong** để chạy riêng file lỗi.
9. Bật lịch 30 phút. Lượt đầu phải chạy ngay; lượt sau bỏ qua PDF đã ghi nhớ. Tắt lịch phải ngăn lượt sau. Chrome, Gmail đã đăng nhập và tool phải hoạt động; máy ngủ hoặc tắt sẽ dừng lịch.
10. Đóng và mở lại app. Key, nhóm, sổ, hàng đợi lỗi và lịch phải còn. Kiểm tra tính năng thư mục nhận PDF để dùng khi website hoặc Gmail không tải tự động được.

## Cổng kỹ thuật

Chạy `scripts/release-check.sh` trước khi tạo gói. Bộ này kiểm tra test Python, cú pháp và luồng tải tiện ích, popup 440 px, nhận diện nút tải PDF và ứng dụng web. Build app phải chạy thêm `packaging/build.py` và `packaging/smoke_app.py`.

Chỉ coi Gmail thật hoàn tất khi một thư nhiều PDF trên chính máy khách đi hết bước 3–5. Kiểm thử DOM không thay thế nghiệm thu Gmail. Website cơ quan nhà nước cần connector riêng; nếu chưa nghiệm thu connector, dùng thư mục nhận PDF làm phương án chính thức.
