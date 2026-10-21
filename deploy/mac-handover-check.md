# Kiểm tra tại iMac trước khi bàn giao

Dùng nhánh `codex/mac-customer-test`. Người triển khai thực hiện các bước cài một lần; khách dùng [hướng dẫn ngắn hằng ngày](mac-user-guide.md).

1. **Mở tool:** kiểm tra Docker Desktop phù hợp chip/macOS, rồi bấm `Mo-So-Ghi-Chep-Mac.command` khi Docker chưa mở. Xác nhận Docker tự khởi động và web mở. Bấm lần nữa chỉ mở lại giao diện.
2. **Thiết lập:** khách tạo mật khẩu và tự nhập DeepSeek API key. Tích đồng ý xử lý dữ liệu, bấm **Lưu kết nối DeepSeek** một lần. Chốt tên và mô tả nhóm với khách. Giao diện mặc định chữ 20px; thử 22px nếu khách cần.
3. **Một PDF có chữ:** dùng tài liệu được phép thử, biết trước nội dung và nhóm đúng. Đưa vào `inbox`, bấm **Quét thư mục**; kiểm tra nhóm, nội dung ngắn, file `.md` và PDF gốc. Sổ mặc định hiển thị mọi nguồn; không cần khách chọn lại nguồn để thấy file. Thử **Sửa nhóm** và tải ghi chú.
4. **Nhiều file và chống trùng:** thử vài PDF, trong đó có một file đã xử lý đổi tên. Xác nhận báo số mới/đã có, không tạo thêm ghi chép hoặc gọi phân tích AI cho file trùng trong luồng thư mục. File lỗi phải có thông báo để thử lại. Xác nhận nút tải sổ hoạt động sau khi chọn ngày.
5. **Lịch thư mục:** bật tự kiểm tra, tạm đặt 1 phút để thử một file mới khi không bấm Quét. Sau khi đạt, trả chu kỳ về 30 phút. Chỉ chạy khi Mac/Docker hoạt động; ngủ/tắt máy sẽ ngừng quét.
6. **PDF scan:** dùng file thực tế được phép thử, bật thử OCR trong **Nội dung & chi phí**, rồi đối chiếu chữ và số liệu với bản gốc. Chỉ nghiệm thu OCR khi API DeepSeek của khách thật sự nhận ảnh và trả chữ đúng. Nếu bị từ chối ảnh hoặc OCR lỗi, tài liệu phải hiện **Cần xem lại**; không coi có dòng trong sổ là đã đọc được scan.
7. **Dừng và mở lại:** bấm `Dung-So-Ghi-Chep-Mac.command`, mở lại, đăng nhập; sổ, nhóm và cấu hình phải còn. Xác nhận đường dẫn trong ghi chép trỏ tới thư mục Mac; `inbox/Da-xu-ly` giữ PDF đã quét.
8. **Nếu dùng Gmail:** cài tiện ích vào Chrome thật của khách, thử một thư có nhiều PDF rồi mới bật lịch 30 phút. Xác nhận file mới/đã có/lỗi và kết quả trong sổ. Khi Gmail không tải được, luồng thư mục vẫn phải dùng được.

Trước khi rời máy, để khách tự làm lại một vòng: **bấm mở tool → chép PDF vào inbox → xem sổ → sửa nhóm**. Bàn giao vị trí thư mục, cách sao lưu `.local` và `inbox`, cùng cách báo lỗi. Không thu thập mật khẩu, API key hoặc tài liệu mật của khách.
