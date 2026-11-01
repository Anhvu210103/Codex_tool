# Kiểm thử 0.9.3 — 01/11/2026

## Kết quả bản chốt

Mã nguồn `b797e24`; [CI 41284282268](https://github.com/Anhvu210103/Codex_tool/actions/runs/41284282268) thành công trên cả bốn hệ máy. Bộ kiểm thử Python, Node, 21 tình huống trình duyệt, tích hợp Chrome native và smoke test ứng dụng đóng gói đều đã qua các bước áp dụng tương ứng.

| Gói test | Tải gói |
| --- | --- |
| Windows x86_64 | [ZIP công khai, không cần đăng nhập](https://github.com/Anhvu210103/Codex_tool/releases/download/windows-v0.9.3/SoGhiChep-Windows-x86_64.zip) |
| Linux x86_64 | [SoGhiChep-Linux-x86_64](https://github.com/Anhvu210103/Codex_tool/actions/runs/41284282268/artifacts/13074732880) |
| Mac Apple Silicon | [DMG công khai, không cần đăng nhập](https://github.com/Anhvu210103/Codex_tool/releases/download/macos-v0.9.3/SoGhiChep-macOS-AppleSilicon.dmg) |
| Mac Intel | [DMG công khai, không cần đăng nhập](https://github.com/Anhvu210103/Codex_tool/releases/download/macos-v0.9.3/SoGhiChep-macOS-Intel.dmg) |

Windows được phát hành lại từ đúng artifact đã kiểm thử bởi [CI xuất bản 41312888897](https://github.com/Anhvu210103/Codex_tool/actions/runs/41312888897). Link công khai đã được tải thử không có thông tin đăng nhập: HTTP 200, ZIP 14.996.600 byte, CRC/SHA256 hợp lệ, chỉ có `SoGhiChep.exe` x86_64 và `HUONG-DAN.txt`. Artifact Linux vẫn cần đăng nhập GitHub.

Hai DMG được giữ nguyên từ bản dựng đã kiểm thử bởi [CI xuất bản Mac 41324420260](https://github.com/Anhvu210103/Codex_tool/actions/runs/41324420260). Tải ẩn danh trả HTTP 200; SHA256 và đuôi UDIF hợp lệ. Apple Silicon: 14.364.673 byte, đọc trực tiếp Mach-O trong DMG xác nhận CPU arm64 (`0x0100000c`). Intel: 14.970.567 byte, xác nhận CPU x86_64 (`0x01000007`). Chỉ giải nén để kiểm tra kiến trúc, không sửa ảnh đĩa hoặc chữ ký ứng dụng.

Các phép thử không dùng tài khoản Gmail khách hoặc gọi API GreenNode thật; hai phần này vẫn cần nghiệm thu tại máy khách.

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

Bổ sung lỗi backend tạm thời cho một PDF ở giữa lượt: phải tiếp tục đủ 20 thư, giữ file lỗi trong hàng đợi, lượt tiếp chỉ tải lại đúng PDF đó và tạo đủ 21 ghi chép. Lượt thứ ba không tải thêm file.

Chromium trong workspace chặn unpacked extensions bằng chính sách quản trị. Không sửa chính sách này; bài kiểm tra native được chạy trên GitHub Actions với Chromium do Playwright cung cấp. Không dùng tài khoản Gmail thật hoặc gọi GreenNode trong bài kiểm tra này.

Bộ kiểm thử Python và các phép thử giao diện của 0.9.2 tiếp tục được chạy. Kết quả native được xác nhận bằng lượt CI của bản chốt.

`tests/browser/extension_batch.py` đã chạy thành công 21 tình huống trong trình duyệt: đủ 20 thư/21 PDF, không tải trùng, thêm PDF vào thư cũ, thử lại file lỗi, ô PDF bị che, Chrome không bắt đầu tải sau click, bấm lại có giới hạn, Close bị bỏ qua và dùng Esc, click không tới nút, thư chưa đọc biến mất khỏi kết quả, chuyển trang, tìm kiếm trống, nhận diện thư bằng URL hoặc metadata, đính kèm hiện muộn và bốn nhánh PDF dùng chung metadata của thư. Bộ này được đưa vào release-check và CI để tránh lệch khỏi mã đang phát hành. Worker trong bộ này được giả lập; bài native riêng dùng API Chrome và backend thật.

Kiểm tra cục bộ: 142 bài unittest Python đạt; ba bộ Node về tải file và tranh chấp lượt chạy đạt; popup, 14 trường hợp DOM nút tải, định danh PDF, khôi phục content session, giao diện quản trị và 21 tình huống batch đều đạt. OCR qua model và Gmail tài khoản khách vẫn cần nghiệm thu thật.

ID của phần tử chứa thư không được dùng làm ID duy nhất cho các PDF bên trong. Khóa mới phân biệt từng tệp, giữ ổn định khi thêm tệp khác, và không đánh dấu tệp lỗi là đã xử lý khi tệp cùng thư thành công. Lịch sử cũ dùng ID chung phải được kiểm tra lại một lần; hash PDF ở backend ngăn tạo ghi chép hoặc gọi AI trùng cho bản đã lưu.

Khi bố cục Gmail không có thẻ đính kèm hỗ trợ nút tải trực tiếp, chuyển ngay sang trình xem PDF; không chờ 3 giây cho một nút không thể xuất hiện trong bố cục ấy. Nhánh này có phép thử DOM và được đi qua trong bộ batch.

## Giới hạn thời gian chờ

Yêu cầu điều khiển từ tiện ích tới localhost có thời hạn 15 giây; chọn thao tác AI có 90 giây; nhập và xử lý PDF có 6 phút. Thời hạn bao gồm đọc thân phản hồi. Lỗi trả thông báo có thể xử lý và luôn giải phóng bộ hẹn giờ; không treo tiện ích vô hạn khi máy chủ ngừng trả dữ liệu.

Trang quản trị cũng có thời hạn 15 giây, riêng tải/đọc lại PDF là 6 phút. Thử lại, thông báo mất kết nối, dữ liệu nhóm dạng danh sách, header CSRF và upload multipart được kiểm tra. Luồng giao diện thật có thêm bước nạp nhóm mẫu.

Thanh công cụ PDF ưu tiên nút có nhãn, sau đó biểu tượng tải nằm giữa In và Thêm, cuối cùng mới dùng nút tải duy nhất ở bố cục khác. Ca có liên kết “Tải xuống” trong nội dung trang được tái hiện trước sửa và được thêm vào bộ 14 trường hợp DOM.

Lượt tải đã được nhận diện ngay từ đầu vẫn được theo dõi khi Chrome mất hơn 15 giây để cung cấp tên file. ID tải bằng 0 trong nhánh đến muộn không làm bấm tải lại. Tiện ích gửi tên PDF gốc bên cạnh đường dẫn Downloads để Markdown mới không bị đổi tên theo hậu tố “(1)” của Chrome; backend kiểm tra tên trước khi xử lý.

Tên gốc có ngoặc số, ví dụ `report (2026).pdf`, vẫn khớp khi Chrome lưu thành `report (2026) (7).pdf`. Chỉ bỏ hậu tố phát sinh ở tên thực tải, giữ số trong tên gốc; phép thử âm ngăn gộp `report.pdf` hoặc `report (2025).pdf` thành tài liệu năm 2026.

## Phục hồi và tải lớn

- Cache AI lỗi được thay bằng kết quả hợp lệ ở lần thử lại, không ghi một cache hit miễn phí giả. Phản hồi API sai cấu trúc vẫn được ghi usage đã trả về và không tạo ghi chép sai.
- Trạng thái đang chạy được ghi trước khi xử lý; khởi động lại nhận ra lượt gián đoạn. Lỗi tạo worker hoặc ghi trạng thái không làm giữ khóa xử lý.
- Lỗi HTTP bất ngờ trả mã tra cứu và ghi stack trace riêng trong errors.log.
- Khi tắt máy chủ, Gmail hoàn tất tài liệu hiện tại rồi ngừng lấy tài liệu tiếp theo.
- Thống kê chi phí đọc lịch sử từng dòng, không nạp snapshot giá và ID tài liệu vào RAM. Phép thử 12.000 dòng với snapshot 2 KB/dòng tái hiện mức cấp phát 33,3 MB trước sửa; bản mới đạt giới hạn dưới 10 MB và vẫn trả đúng 50 lượt gần nhất.
- Backend và tiện ích có phiên bản đối chiếu; báo cáo tiện ích ghi phiên bản tool đang kết nối. Phiên bản backend giữ nguyên cho tới khi khởi động lại, kể cả khi tệp giao diện trên đĩa đã cập nhật.
- App mở qua Finder tìm Poppler trong PATH, sau đó ở Homebrew Apple Silicon và Intel. Thiếu chương trình chuyển ảnh báo đúng thiếu Poppler, dừng các trang còn lại trước khi gọi OCR trả phí và vẫn giữ phần chữ đã lấy được.
