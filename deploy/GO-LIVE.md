# Checklist go-live

## Trước ngày cài

- [ ] Chốt hệ điều hành và chip máy khách; tải đúng gói Linux, Mac Intel hoặc Mac Apple Silicon.
- [ ] Bản phát hành và tiện ích cùng phiên bản; tiện ích hiện **v0.9.1**.
- [ ] Chạy `scripts/release-check.sh` thành công và lưu mã commit đã bàn giao.
- [ ] Không có `.local/`, `.env`, API key, OAuth JSON, token hoặc dữ liệu khách trong gói/Git.
- [ ] Có GreenNode / VNG Cloud API key hoạt động, model được cấp quyền và số dư/hạn mức phù hợp.
- [ ] Nếu cần OCR PDF scan: `pdftoppm` chạy được (`poppler-utils` trên Linux, `brew install poppler` trên Mac; Docker đã có sẵn).
- [ ] Nếu dùng Gmail API, OAuth redirect URI đúng địa chỉ/cổng thực tế. Nếu dùng tiện ích, Chrome đã được phép nạp tiện ích nội bộ.
- [ ] Có thư mục nhận PDF thủ công làm đường dự phòng.

## Nghiệm thu tại máy khách

- [ ] Tạo mật khẩu quản trị riêng, đăng nhập và đổi lại được.
- [ ] PDF có chữ tạo nội dung ngắn, nhóm và file Markdown có nội dung, tên bám theo file gốc.
- [ ] PDF scan đi qua OCR hoặc vào Cần xem lại với lý do rõ ràng; không có `.md` 0 byte.
- [ ] Một Gmail có nhiều PDF được xử lý hết; một file lỗi không làm dừng các thư còn lại.
- [ ] Lượt quét kế tiếp không gọi lại AI cho tài liệu đã có; báo cáo tách mới, trùng và lỗi.
- [ ] Sửa nhóm cập nhật file Markdown mà không gọi AI.
- [ ] Token và chi phí hiện trên Tổng quan; đối chiếu một lượt với usage của nhà cung cấp.
- [ ] Lịch chạy ngay khi bật, chạy lại sau 30 phút và ngừng khi tắt. Kiểm tra lại sau khi khởi động máy.
- [ ] Khách tự mở app, mở sổ, xem báo cáo lỗi, thử lại file lỗi và dùng thư mục nhận PDF được.

## Dữ liệu và bàn giao

- [ ] Sao lưu thư mục dữ liệu khi app đã dừng; thử khôi phục trên bản sao.
- [ ] Ghi lại vị trí dữ liệu, thư mục nhận PDF, phiên bản app/extension và người giữ API key.
- [ ] Không gửi API key, token, OAuth JSON hoặc bản sao dữ liệu qua chat.
- [ ] Thống nhất giới hạn hỗ trợ: Gmail và thư mục PDF đã nghiệm thu; website khác cần connector riêng.
- [ ] Ghi nhận ba phép thử thật chưa thể thay bằng test tự động: GreenNode OCR ảnh, Gmail giao diện tài khoản khách và app trên đúng máy Mac khách.

Go-live chỉ đạt khi mọi mục bắt buộc trên máy khách đã được đánh dấu. Lỗi còn lại phải có người phụ trách, phương án dự phòng và thời hạn xử lý.
