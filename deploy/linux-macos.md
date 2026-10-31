# Cùng một quy trình trên Linux và macOS

Linux, Mac Intel và Mac Apple Silicon dùng cùng mã xử lý, giao diện, tiện ích Chrome và định dạng dữ liệu. Đây là sự thống nhất quy trình; dữ liệu của các máy chưa tự đồng bộ qua Internet.

| Bước | Linux và macOS |
| --- | --- |
| Mở tool | Bấm ứng dụng Sổ ghi chép, tool mở giao diện quản trị. |
| Cài AI | Lưu GreenNode / VNG Cloud API key, kiểm tra model và nhóm. Cấu hình gửi dữ liệu được bật sẵn cho nhà cung cấp này. |
| Dùng tiện ích | Tải cùng ZIP tiện ích trong Cài đặt, cài vào Chrome, ghép nối bằng địa chỉ tool và mã trên chính máy đó. |
| Chạy AI thao tác | Mở Gmail đã đăng nhập bình thường trong Chrome, tìm thư có PDF, bấm Xử lý tối đa 20 thư đang hiện. Có nút Dừng. |
| Xử lý tài liệu | PDF có chữ → Markdown trên máy → GreenNode / VNG Cloud phân nhóm và tóm tắt → ghi sổ; mỗi thư mục nhóm giữ bản Markdown. |
| PDF scan | Thử OCR qua model GreenNode / VNG Cloud; nếu API không nhận ảnh hoặc thất bại thì giữ bản gốc và tạo ghi chú Cần xem lại. Cần Poppler để chuyển PDF thành ảnh, không cần Tesseract. |
| Xem kết quả | Sổ ghi chép → AI thao tác → xem đường dẫn Markdown theo nhóm, Mở thư mục tài liệu hoặc Tải Markdown. |
| Sửa nhóm | Sửa trong sổ, bản Markdown theo nhóm cập nhật theo, không gọi AI lại. |
| Tắt | Bấm Tắt tool. Đóng tab không tắt dịch vụ; máy ngủ hoặc tắt thì việc xử lý ngừng. |

Gmail API vẫn là nguồn riêng có thể kiểm tra theo lịch đã lưu trên cả hai hệ điều hành. Tiện ích xử lý thủ công tối đa 20 thư đang hiện; khi bật lịch, tiện ích quét ngay rồi chạy mỗi 30 phút, tối đa 100 thư mỗi trang và 20 trang mỗi lượt.

## Khác biệt do hệ điều hành

| Hạng mục | Linux | macOS |
| --- | --- | --- |
| App đóng gói | SoGhiChep-Linux-x86_64 | SoGhiChep-macOS-Intel hoặc SoGhiChep-macOS-AppleSilicon |
| Dữ liệu app mặc định | `~/.local/share/so-ghi-chep/` hoặc XDG_DATA_HOME | `~/Library/Application Support/SoGhiChep/` |
| Mở thư mục | Trình quản lý file mặc định qua xdg-open | Finder qua open |
| Mã nguồn đã cài .venv | Mo-So-Ghi-Chep.sh | Mo-So-Ghi-Chep.command |

Bản mã nguồn dùng `.local/` trong thư mục repository trên cả hai hệ điều hành. Mọi nguồn có cấu trúc giống nhau: `ai/`, `gmail/`, `pdf/`, `folder/`; bên trong có `files/`, `Markdown/`, `Theo-nhom/`, `Can-xem-lai/` và SQLite. Thay app không thay dữ liệu. Mã ghép nối và địa chỉ/cổng được cấu hình riêng cho từng máy. Dùng Chrome cho tiện ích; Safari/Firefox chưa được hỗ trợ.

Mac app thử nghiệm chưa ký Developer ID/notarize nên có thể cần người dùng xác nhận trong Privacy & Security theo cơ chế của macOS. Không tắt Gatekeeper. Phải chọn bản theo chip và kiểm tra trên phiên bản macOS thực tế của khách.

## Xác nhận tính đồng nhất

CI dùng cùng bộ kiểm thử trên Ubuntu, Mac Intel và Apple Silicon. Sau khi build, mỗi job khởi động chính app đã đóng gói với dữ liệu tạm, kiểm tra đăng nhập, PDF chữ → Markdown/nhóm, PDF scan → Cần xem lại và ZIP tiện ích. Phép thử không gọi GreenNode thật, không đăng nhập Gmail khách và không mở Finder/file manager. Các bước đó vẫn cần kiểm chứng trên máy khách với quyền truy cập hợp lệ. Không coi cấu hình CI là kết quả CI đã thành công.

## Phương án tải PDF thủ công

Trên cả Linux và macOS, trang **Cài đặt → Thư mục nhận PDF thủ công** hiển thị đường dẫn `Downloads/So-Ghi-Chep-Inbox` của người dùng đang chạy tool. Khách tải PDF vào đây khi connector website không hoạt động. Có thể quét ngay hoặc bật quét theo chu kỳ. Giữ Chrome tải file hoàn tất trước khi quét; các file `.crdownload`, symlink, PDF đang thay đổi, quá dung lượng hoặc sai định dạng không được nhập. PDF đã xử lý được chuyển vào thư mục con `Da-xu-ly`.
