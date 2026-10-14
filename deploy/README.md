# Triển khai cho khách

Bản này phục vụ **một quản trị viên / một Gmail / một máy chủ, có tải PDF trực tiếp**. Chạy đúng một process web cho một thư mục dữ liệu. Không chạy thêm CLI `watch` hoặc nhiều worker web để xử lý cùng nguồn. Đóng trình duyệt không dừng lịch; tắt máy chủ/dịch vụ sẽ dừng lịch. Khi khởi động lại, lịch bật sẽ chờ đủ chu kỳ rồi quét lại toàn bộ email khớp query và bỏ qua các ID đã xử lý. Không có hàng đợi bền vững cho thao tác đang chạy dở.

## Một lần bởi quản trị viên kỹ thuật

1. Chọn máy chủ Linux có Python 3.11+, domain và chứng chỉ HTTPS hợp lệ. Đưa mã nguồn vào `/opt/mailnotes`, tạo tài khoản dịch vụ `mailnotes`, cho tài khoản đó sở hữu `.local/` (quyền thư mục 0700). Mã nguồn có thể chỉ cho phép đọc.
2. Tạo `.venv`, cài phiên bản đã khóa:

   ```bash
   cd /opt/mailnotes
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements-web.txt
   .venv/bin/python -m unittest discover -s tests -v
   ```

3. Tạo `/etc/mailnotes.env` riêng, quyền 0600 do root quản lý; nhập qua công cụ quản lý secrets hoặc editor trên máy chủ, không commit file này:

   ```text
   MAILNOTES_PUBLIC_URL=https://notes.your-domain.example
   MAILNOTES_ADMIN_PASSWORD=<mật khẩu riêng ít nhất 12 ký tự>
   ```

   Thay URL và mật khẩu bằng giá trị thật. Biến mật khẩu chỉ dùng khởi tạo khi chưa có file `.local/admin/password.json`; sau đó mật khẩu được quản lý bằng hash PBKDF2, có thể đổi trên web. Không cần đặt `OPENAI_API_KEY` để dùng trích đoạn. API key có thể nhập sau trên web (lưu file riêng quyền 0600).

4. Dùng mẫu `mailnotes.service` cho systemd, điều chỉnh tài khoản và đường dẫn nếu khác. Reverse proxy HTTPS tới `127.0.0.1:8080` theo `nginx.conf.example`. Chỉ mở cổng HTTPS cho khách, giữ cổng backend nội bộ. Không ghi query string của `/oauth/callback` vào access log.
5. Quản trị viên kỹ thuật cài và bật service bằng systemd. Kiểm tra truy cập trang đăng nhập qua domain HTTPS. Backend dùng Waitress, không dùng Flask debug server. Giới hạn đăng nhập sai tính theo IP backend; nếu tất cả truy cập qua một proxy, giới hạn 5 lần/5 phút sẽ dùng chung. Có thể thêm rate limit phù hợp ở proxy.
6. Bật Gmail API, cấu hình Google OAuth consent screen và OAuth client loại **Web application**. Đặt Authorized redirect URI chính xác bằng URI trong Cài đặt. Google có thể yêu cầu xác minh ứng dụng khi cung cấp rộng rãi quyền Gmail; chế độ Testing chỉ dành cho test users và refresh token có thể hết hạn. Không hứa đăng nhập lâu dài trước khi hoàn tất cấu hình Google.
7. Vào web, tải file JSON client và kết nối Gmail. Chạy một lượt với vài email thật có nhãn thử, đối chiếu nội dung/người gửi/nhóm/link trước khi bật lịch. OAuth và API thật chưa được kiểm chứng trong môi trường phát triển vì không có credentials.

## Khách tự làm trên web

- Đổi nguồn mẫu/Gmail, bộ lọc Gmail, chu kỳ, múi giờ; bật/tắt lịch.
- Thêm/xóa nhóm, từ khóa và điều kiện người gửi. Quy tắc mới áp dụng email chưa xử lý.
- Chọn rules + trích đoạn miễn phí hoặc AI phân nhóm/tóm tắt chung. Chọn DeepSeek/OpenAI, xác nhận đồng ý gửi nội dung, lưu/xóa key riêng cho từng nhà cung cấp và đặt giới hạn đầu vào.
- Bấm Chạy ngay, theo dõi trạng thái/lỗi gần nhất.
- Tìm ghi chép, lọc ngày/nhóm/nguồn và tải toàn bộ sổ Markdown của một ngày. File tải gồm toàn bộ ngày, không chỉ các hàng đang lọc bằng từ khóa.
- Kết nối lại Gmail khi quyền hết hạn, ngắt kết nối và đổi mật khẩu quản trị.

Website mới và thay đổi cơ chế đăng nhập vẫn cần bộ kết nối riêng; đây chưa phải công cụ thu thập được mọi URL.

## Dữ liệu và vận hành

Cấu hình web nằm tại `.local/admin/settings.json`, tách khỏi `config.json` của CLI. File nhạy cảm gồm `.local/admin/session.json`, `gmail-client.json`, `gmail-token.json`, `ai-key.json`, `deepseek-key.json` và `password.json`. Không phục vụ `.local/` qua web server, không đưa vào Git hoặc log. API chỉ trả trạng thái có/chưa có secret, không trả lại giá trị. API key và token được lưu trên đĩa máy chủ, chưa có vault hoặc mã hóa ổ đĩa tích hợp; hạn chế tài khoản có quyền đọc và dùng ổ đĩa/backup mã hóa theo yêu cầu khách.

Dữ liệu mẫu: `.local/demo/`. Dữ liệu Gmail web: `.local/gmail/`. CLI Gmail cũ dùng `.local/notes.sqlite3`; chưa tự di chuyển dữ liệu hoặc token CLI sang web. UI hiển thị tối đa 500 kết quả một lần; file Markdown của ngày chứa đầy đủ. Đổi rules không tự phân loại lại ghi chép cũ. Ngắt Gmail chỉ xóa token cục bộ, không xóa sổ hoặc tự thu hồi quyền trên tài khoản Google; khách có thể thu hồi trong Google Account.

Sao lưu `.local/` khi dịch vụ đã dừng để có snapshot SQLite nhất quán; bảo vệ backup tương tự dữ liệu gốc. Khôi phục đúng bản code và cả thư mục dữ liệu. Không thay thế/ghi đè file bí mật của khách khi nâng cấp. Kiểm thử trước trên bản sao dữ liệu.

Service restart không giữ phiên xử lý đang chạy, nhưng các email đã commit SQLite không tóm tắt lại. Nếu API đã trả kết quả nhưng process chết trước commit, email đó có thể phải gọi AI lại. Không cam kết tránh chi phí trùng tuyệt đối trong tình huống này.


## PDF và AI

Bật Đọc PDF đính kèm Gmail trong Cài đặt: email có PDF tạo một ghi chép cho mỗi PDF (không tạo thêm ghi chép riêng cho thân email); email không có PDF vẫn xử lý nội dung thư. PDF upload trực tiếp lưu riêng tại `.local/pdf/`, PDF đính kèm tại `.local/gmail/files/`. Các file gốc có tên theo SHA-256, quyền 0600. UI cho phép tải lại bản gốc qua phiên đăng nhập. Sửa nhóm bằng tay không gọi AI; xem cảnh báo gốc để biết giới hạn tóm tắt.

PDF tối đa 20 MB; đọc lớp văn bản tối đa 100 trang/100.000 ký tự. Giới hạn đầu vào AI được khách chỉnh; phần vượt giới hạn không được gửi và ghi chép có cảnh báo Cần xem lại. PDF lỗi, có mật khẩu hoặc scan chưa OCR được đưa vào Cần xem lại, không gửi nội dung rỗng cho AI. File Word/Excel và website chưa được hỗ trợ.

Một request AI trả JSON nhóm + tóm tắt. Nhóm ngoài danh sách, confidence dưới 0.65 (do mô hình tự báo, không phải độ chính xác đã đo), hoặc needs_review sẽ vào Cần xem lại. Cache SQLite gắn với nhà cung cấp, mô hình, prompt, nội dung gửi và mô tả nhóm; tránh gọi lại kết quả giống nhau trong cùng nguồn. Cache không dùng chung giữa Gmail/PDF upload. Khi PDF đã lưu, upload lại không gọi AI. Chọn Xử lý lại PDF đã có nếu cần áp dụng cấu hình/OCR mới; thao tác này thay nhóm/tóm tắt đã sửa bằng tay và có thể phát sinh phí. Nếu prompt/input không đổi, cache vẫn được dùng.

DeepSeek dùng endpoint cố định `https://api.deepseek.com/chat/completions`, model mặc định `deepseek-chat`; không cho nhập endpoint tùy ý. Cho phép domain `api.deepseek.com` trong mạng máy chủ. Key nhập qua web hoặc `DEEPSEEK_API_KEY`; OpenAI vẫn dùng key riêng. Không có key thật trong repo. Giá và quota phụ thuộc tài khoản nhà cung cấp; chưa xác nhận chi phí hay độ chính xác trên tài liệu khách.

OCR là tùy chọn chạy cục bộ, tối đa 20 trang với ngân sách thời gian khoảng 180 giây cho các lệnh OCR. Để cài trên Ubuntu/Debian:

```bash
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-vie
```

Trên Mac có Homebrew:

```bash
brew install poppler tesseract tesseract-lang
```

Kiểm tra `tesseract --list-langs` có `vie` và `eng`, rồi bật OCR trên web. Kết quả OCR vẫn đánh dấu Cần xem lại để đối chiếu bản gốc. Môi trường phát triển hiện thiếu ngôn ngữ `vie`, nên chưa kiểm chứng OCR tiếng Việt thật; PDF có chữ và cơ chế chuyển scan sang review đã được kiểm chứng.
