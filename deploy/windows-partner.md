# Hướng dẫn dùng Sổ ghi chép trên Windows

## Cài lần đầu

1. Cài **Docker Desktop** cho Windows, mở ứng dụng và đợi trạng thái **Engine running**. Máy cần chạy được Docker Compose. Không cần cài Python.
2. Tải nhánh `codex/windows-partner-test` từ GitHub dưới dạng ZIP, giải nén vào một thư mục cố định, ví dụ `D:\Tcom_AI\Codex_tool`. Giữ nguyên toàn bộ thư mục; đừng chỉ chép file `.cmd`.
3. Bấm đúp **`Mo-So-Ghi-Chep-Windows.cmd`**. Lượt đầu Docker tải và dựng image nên có thể mất vài phút. Khi trình duyệt mở `http://localhost:8080`, tạo mật khẩu quản trị riêng dài ít nhất 12 ký tự. Không gửi mật khẩu hay API key cho người hỗ trợ.
4. Những lần sau: mở Docker Desktop, bấm đúp file `.cmd`, rồi đăng nhập web. Nếu trình duyệt không tự mở, nhập `http://localhost:8080` vào thanh địa chỉ.

Tool chỉ công bố cổng 8080 trên máy này. Nếu cổng đã bị ứng dụng khác chiếm, Docker sẽ báo lỗi; dừng ứng dụng đang dùng cổng rồi chạy lại. Đóng tab trình duyệt không dừng lịch xử lý. Muốn dừng hẳn, mở PowerShell tại thư mục tool và chạy `docker compose down`.

## Thiết lập để dùng

1. Vào **Cài đặt → Nội dung & chi phí**. Nhập DeepSeek API key, bấm **Lưu key riêng**, tích đồng ý gửi dữ liệu và bấm **Lưu cài đặt**. Đơn giá token đã có mặc định; số tiền trên Tổng quan chỉ là ước tính.
2. Vào **Nhóm tài liệu**. Kiểm tra tên/mô tả nhóm, thêm nhóm nếu cần rồi bấm **Lưu nhóm**. Một tài liệu có thể vào nhiều nhóm; tài liệu chưa chắc chắn vào **Cần xem lại**.
3. Để thử không cần Gmail, chép PDF vào thư mục `inbox` nằm cạnh file `.cmd`. Chờ ít nhất 3 giây, vào **Cài đặt → Thư mục nhận PDF thủ công → Quét thư mục ngay**. Sau đó chọn **Thư mục nhận PDF** trên Tổng quan hoặc Sổ ghi chép. Nếu muốn tự quét theo chu kỳ, tích tùy chọn tự quét và lưu cài đặt. File đã xử lý được chuyển sang `inbox\Da-xu-ly`; file lỗi ở lại để thử lại.
4. Muốn dùng **Gmail API** thì cần cấu hình Google OAuth trong Cài đặt. Cách này chạy theo lịch trong container và không cần mở Chrome. Đặt đúng redirect URI mà trang Cài đặt hiển thị (`http://localhost:8080/oauth/callback` nếu dùng cổng mặc định).

## Tiện ích Chrome thao tác Gmail

Trong **Cài đặt → Tiện ích Chrome**, tải ZIP, giải nén rồi mở `chrome://extensions`. Bật **Developer mode**, chọn **Load unpacked** và đúng thư mục có `manifest.json`. Ghép nối địa chỉ `http://localhost:8080` và mã lấy từ trang Cài đặt. Mở Gmail đã đăng nhập trong Chrome, thử **1 thư** trước, xem báo cáo và kiểm tra kết quả ở nguồn **Gmail qua tiện ích Chrome**. Khi ổn mới bật lịch 30 phút. Gmail API và tiện ích là hai lịch riêng; chỉ bật lịch thực sự cần dùng.

Trên Windows, tiện ích chưa có đường nhập trực tiếp PDF từ thư mục Downloads như Linux. Nó thử đọc lại URL sau khi Chrome tải; nếu Google chặn URL, tiện ích sẽ yêu cầu chọn PDF đã tải bằng tay. Khi đó hãy dùng thư mục `inbox` để có luồng ổn định. Cách tự thao tác Gmail trên Windows cần kiểm thử với Gmail thật của người dùng trước khi giao chạy nền lâu dài.

## Tài liệu, cập nhật và kiểm tra lỗi

- Dữ liệu, sổ, cấu hình và token nằm ở `.local` cạnh file `.cmd`; PDF đưa vào ở `inbox`. Mỗi nguồn có thư mục riêng. PDF gốc giữ một bản trong `files/`; bản theo nhóm là file `.md` ở `Theo-nhom/` hoặc `Can-xem-lai/`. Đường dẫn trong sổ là **đường dẫn trong container** (`/app/.local/...`); trên Windows, thay `/app/.local/` bằng đường dẫn tới `.local\` trong thư mục tool để mở bằng Explorer.
- Để cập nhật bản ZIP: dừng bằng `docker compose down`, sao lưu `.local` và `inbox`, giải nén mã mới vào **cùng thư mục**, giữ nguyên hai thư mục đó, rồi bấm file `.cmd`. Nếu đã clone bằng Git, chạy `git pull origin codex/windows-partner-test` trước khi bấm file `.cmd`.
- Sau khi cập nhật tiện ích, tải ZIP mới và **Load unpacked** từ thư mục mới, hoặc thay đúng thư mục Chrome đang nạp rồi bấm **Reload**. Chrome Reload không tự thay một thư mục cũ trong Downloads.
- Trạng thái container: `docker compose ps`. Xem lỗi: `docker compose logs --tail=100 mailnotes`. Kiểm tra web: `http://localhost:8080/health`. Nếu trang web trắng, tải lại bằng Ctrl+Shift+R sau khi container đã chạy.

Bản Windows này dùng Docker Desktop; chưa phải ứng dụng `.exe` độc lập. PDF có chữ được trích trên máy chủ container. Với PDF scan, bật OCR qua DeepSeek nếu cần; kết quả OCR cần đối chiếu bản gốc và có thể phát sinh phí. Không cần cấu hình OCR cục bộ.
