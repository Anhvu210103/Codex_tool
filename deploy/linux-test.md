# Chốt luồng Linux trước khi bàn giao

Phạm vi: tiện ích Chrome thao tác tối đa 20 thư/lượt và mọi PDF nhìn thấy trong mỗi thư; tool lấy PDF, tạo Markdown, dùng DeepSeek phân nhóm/tóm tắt, lưu vào nguồn AI thao tác và xuất thư mục nhóm. Bản scan vào Cần xem lại, không chạy OCR. Gmail API là bộ kết nối theo lịch riêng, không phải lịch tự thao tác của tiện ích.

1. Mở tool và Chrome bình thường. Lưu DeepSeek key trong tool, bật AI và lưu nhóm mẫu. Ghép nối tiện ích phiên bản 0.4.5 với đúng địa chỉ/cổng tool. Sau cập nhật, bấm Reload tại `chrome://extensions` rồi tải lại Gmail.
2. Trong Gmail tìm một email mẫu có PDF bôi đen/copy chữ được. Bấm Thử 1 thư, để tiện ích tự thao tác và không bấm tải hộ. Báo cáo phải có `tim-nut-tai`, `da-bam-tai`, `chrome-bat-dau`, `chrome-xong`, `dong-pdf`. Nếu thiếu `da-bam-tai`, Gmail chưa nhận click; nếu thiếu `chrome-bat-dau`, Chrome chưa tạo lượt tải. Tiện ích thử Esc khi nút Đóng không hoạt động. Kiểm tra Ctrl+J và sao chép Báo cáo lần chạy nếu còn lỗi.
3. Trên Linux, tool ưu tiên nhập đúng file PDF vừa tải trong thư mục Downloads do XDG cấu hình; không quét thư mục. Không đọc đường dẫn ngoài thư mục đó hoặc liên kết trỏ ra ngoài. Nếu không nhập trực tiếp được, tiện ích thử URL tệp đính kèm; có ô chọn file bằng tay khi Google không cho đọc lại URL.
4. Tiện ích phải hiện tên file, nhóm và đường dẫn PDF trên máy. Kiểm tra Sổ ghi chép → AI thao tác: có dòng tài liệu, tóm tắt, nhóm và cột PDF trên máy. Bấm Mở thư mục tài liệu: có PDF gốc trong files/, Markdown trong Markdown/, và cả PDF lẫn bản tóm tắt Markdown trong Theo-nhom/. Mỗi tài liệu nhiều nhóm có bản PDF ở mỗi thư mục nhóm.
5. Sửa nhóm trong sổ: bản Markdown phải chuyển đúng nhóm mà không tăng số lượt gọi AI. Đọc lại cùng PDF với cấu hình giống nhau: không tạo dòng trùng; cache phân nhóm không thêm token. Các lượt AI chọn nút vẫn có token riêng.
6. Thử PDF scan: giữ gốc và tạo ghi chú trong Can-xem-lai/, không gọi DeepSeek để đoán nội dung. Tiện ích hiện rõ lý do cần kiểm tra.
7. Dừng giữa lượt: không được bấm tiếp. Lượt AI đã gửi hoặc tài liệu đã chuyển tới tool có thể hoàn tất và tính phí. Đóng/mở lại app phải giữ key, nhóm và sổ; chọn đúng cổng nếu app đã phải đổi cổng.

Kiểm thử tự động bao gồm file tải chưa hoàn tất, tên file báo muộn, chuyển tab sau khi tải bắt đầu, nhập PDF local, chặn đường dẫn ngoài Downloads, file tải gián đoạn, fallback URL, nguồn AI, nhóm/Markdown và giới hạn file descriptor. Bản app Linux được kiểm tra sau đóng gói với PDF mẫu và API nội bộ; không gọi DeepSeek thật hoặc đăng nhập Gmail khách trong phép thử này.

Chỉ coi luồng Gmail thực tế hoàn tất khi một PDF mẫu trên chính máy người dùng đi hết bước 2–4. Website cơ quan nhà nước và Mac được kiểm chứng sau; không dùng kết quả mô phỏng Gmail để khẳng định đã hỗ trợ website khác.
