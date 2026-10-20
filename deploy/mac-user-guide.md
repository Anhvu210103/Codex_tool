# Dùng Sổ ghi chép hằng ngày trên Mac

## Mở và dừng

Mở **Docker Desktop**, đợi ứng dụng sẵn sàng, rồi trong Finder bấm đúp `Mo-So-Ghi-Chep-Mac.command` ở thư mục Sổ ghi chép. Tool mở tại `http://localhost:8080`; đăng nhập bằng mật khẩu đã tạo. Muốn dừng hẳn, bấm đúp `Dung-So-Ghi-Chep-Mac.command`. Đóng tab trình duyệt chỉ đóng giao diện; máy ngủ hoặc tắt sẽ ngừng lịch quét.

## Xử lý tài liệu

1. Tải PDF từ website/email về Mac. Trong Finder, mở thư mục Sổ ghi chép và chép PDF vào **`inbox/`**. Chờ tải và chép file hoàn tất.
2. Trên **Tổng quan**, bấm **Quét thư mục**. Nếu đã bật tự quét trong **Cài đặt → Thư mục nhận PDF thủ công**, tool sẽ kiểm tra theo chu kỳ đã lưu khi Mac đang chạy. File xử lý xong chuyển vào `inbox/Da-xu-ly`.
3. Vào **Sổ ghi chép**, chọn nguồn **Thư mục nhận PDF**. Xem nhóm, nội dung ngắn và đường dẫn Markdown. Đường dẫn `/app/.local/...` trong sổ tương ứng với `.local/...` ở thư mục tool trên Mac. Nếu chưa thấy, kiểm tra bộ lọc nguồn/ngày và xem thông báo quét trên Tổng quan.
4. Nếu nhóm chưa đúng, bấm **Sửa nhóm** ở dòng tài liệu. Việc này không gọi AI lại. Với tài liệu **Cần xem lại**, mở PDF gốc và đối chiếu nội dung trước khi sử dụng.

Chỉ thử tải PDF trực tiếp ở Sổ ghi chép khi cần xử lý một file riêng. Cùng một file đã xử lý sẽ được chống trùng; nút **Đọc lại PDF** có thể gọi AI và phát sinh phí. Trang **Tổng quan** hiển thị token và tiền AI **ước tính**, không phải hóa đơn.

PDF scan không có chữ cần OCR. Trước khi quét, bật **Dùng OCR qua DeepSeek cho PDF scan** trong Cài đặt và lưu. Tool thử chuyển từng trang thành ảnh rồi gửi qua DeepSeek; kết quả cần đối chiếu với bản gốc. Nếu API không chấp nhận ảnh hoặc OCR lỗi, file vào **Cần xem lại**. Không tự tin dùng tóm tắt của một file chưa đọc được chữ.

## Nếu gặp lỗi

- **Trang không mở:** kiểm tra Docker Desktop đã chạy, bấm lại file mở, thử nhập `http://localhost:8080` vào trình duyệt.
- **PDF chưa xuất hiện:** kiểm tra file đã nằm trực tiếp trong `inbox/`, không còn đang tải, rồi bấm **Quét thư mục**; xem file đã chuyển vào `Da-xu-ly` chưa.
- **Chữ quá nhỏ / bảng bị ngắt:** góc trên chọn **Cỡ chữ → Lớn**; bảng Sổ ghi chép có thể cuộn ngang trên màn hình hẹp.
- **PDF scan vào Cần xem lại:** mở PDF gốc, kiểm tra thông báo OCR và báo người triển khai. Đừng xóa file gốc.

Gmail qua tiện ích hoặc Gmail API là nguồn bổ sung, chỉ bật sau khi luồng thư mục đã dùng ổn. Không chia sẻ mật khẩu, DeepSeek API key, mã ghép nối hoặc thư mục `.local/`.
