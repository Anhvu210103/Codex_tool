# Mailnotes — Gmail → sổ ghi chép theo ngày

MVP đọc nội dung Gmail (không tải file đính kèm), phân loại theo rules, chống xử lý trùng bằng SQLite và xuất Sổ ghi chép dạng bảng Markdown theo ngày nhận email. Bảng gồm giờ nhận, tiêu đề, người gửi, phân loại, nội dung ngắn và nguồn; giờ hiển thị theo múi giờ cấu hình. Chỉ đọc Gmail, không gửi thư, không đổi nhãn hoặc đánh dấu đã đọc.

## Trang quản trị web

Khách tự chỉnh nguồn Gmail, lịch chạy, rules phân loại, múi giờ, độ dài trích đoạn hoặc mô hình AI. Sổ dạng bảng có tìm kiếm, lọc theo ngày/nhóm và tải Markdown. Có đăng nhập, đổi mật khẩu và trạng thái xử lý gần nhất.

```bash
cd /workspace/Codex_tool
python -m venv .venv
.venv/bin/python -m pip install -r requirements-web.txt
.venv/bin/python -m mailnotes.web
```

Mặc định dịch vụ nghe trên loopback, cổng 8080. Trên máy của bạn, mở trình duyệt tới dịch vụ đó, tạo mật khẩu (ít nhất 12 ký tự), rồi chọn **Thử dữ liệu mẫu**. Trong môi trường cloud này, không có web preview công khai; dùng các ảnh trong `.local/screenshots/` để xem giao diện đã kiểm thử. Máy cloud không tương đương dịch vụ luôn hoạt động cho khách.

Các trang: **Tổng quan · Sổ ghi chép · Quy tắc phân loại · Cài đặt**. Lịch mặc định tắt, nguồn mặc định là mẫu. Lưu cài đặt sẽ áp dụng cho lượt tiếp theo; không thay đổi lượt đang chạy. Dữ liệu mẫu luôn dùng trích đoạn miễn phí.

Gmail trên web dùng OAuth client loại **Web application**, không dùng client Desktop của CLI bên dưới. Trang Cài đặt hiển thị redirect URI chính xác, nhận file JSON client và nút kết nối Google. Việc thiết lập Google Cloud và domain HTTPS cần quản trị viên kỹ thuật thực hiện một lần; các thay đổi hằng ngày do khách tự làm trên web.

Cấu hình web lưu riêng tại `.local/admin/settings.json`, không ghi đè `config.json`. Web không đọc cấu hình hay token CLI cũ tự động. Không chạy web scheduler cùng CLI `watch` hoặc nhiều process web trên cùng dữ liệu.

Xem [hướng dẫn triển khai cho khách](deploy/README.md) và mẫu systemd/reverse proxy. Các thư viện web đã khóa phiên bản trong `requirements-web.txt`; CLI trích đoạn vẫn chỉ dùng thư viện chuẩn. Chạy toàn bộ kiểm thử bằng `.venv/bin/python -m unittest discover -s tests -v` sau khi cài dependency web.

## Chạy ngay với dữ liệu mẫu

Yêu cầu Python 3.11+. Chế độ mặc định không cần cài thư viện ngoài.

```bash
cd /workspace/Codex_tool
python -m mailnotes.cli demo
python -m unittest discover -s tests -p test_workflow.py -v
```

Sổ mẫu nằm tại `.local/demo/notebooks/2026-10-13.md`. Chạy lại không tạo bản trùng. Dữ liệu mẫu không phải văn bản pháp luật thực tế.

## Kết nối Gmail thật

1. Tạo project trong Google Cloud Console, bật Gmail API.
2. Cấu hình OAuth consent screen; nếu ứng dụng đang ở chế độ Testing, thêm tài khoản Gmail của bạn vào Test users. Tạo OAuth client loại **Desktop app**, tải JSON credentials.
3. Lưu file ở `.local/credentials.json` trên máy chạy tool. Không commit hoặc gửi credentials/token trong chat.
4. Tạo nhãn `codex-demo` trong Gmail và gắn vào vài email muốn thử.
5. Chạy xác thực trên máy có trình duyệt:

```bash
python -m mailnotes.cli auth
python -m mailnotes.cli once
python -m mailnotes.cli watch
```

`auth` dùng callback loopback trên cùng máy chạy lệnh, có state và PKCE. Trình duyệt trên laptop không thể dùng callback loopback của máy cloud khác. Nếu cloud không có trình duyệt, chạy bước auth trên máy cá nhân với cùng code rồi chuyển `.local/credentials.json` và `.local/token.json` đến cloud qua kênh truyền file bảo mật do bạn quản lý; không dán vào chat. Chỉ token Gmail read-only được yêu cầu. Token được lưu với quyền file 0600 và được tự refresh. Google có thể thu hồi/hết hạn refresh token (đặc biệt khi consent screen ở Testing); lúc đó cần auth lại.

Sổ Gmail nằm tại `.local/notebooks/`; database tại `.local/notes.sqlite3`. Có thể xem Markdown trong trình soạn thảo. Link email gốc mặc định dùng tài khoản Gmail ở vị trí `/u/0`; nếu đăng nhập nhiều tài khoản, mở trong đúng tài khoản nguồn.

`watch` chạy mỗi 1.800 giây sau lượt trước. Giữ process chạy bằng supervisor của máy triển khai; dừng bằng Ctrl+C. Đây chưa phải dịch vụ lưu trữ luôn hoạt động của Codex. Chỉ chạy một worker trên cùng thư mục dữ liệu. Khi polling lỗi, không ghi nhận email lỗi là đã xử lý, và thử lại ở chu kỳ tiếp theo; nội dung thư, token và response lỗi không được ghi ra log.

## Rules

Sửa `config.json`:

- `gmail_query`: cú pháp tìm kiếm Gmail, mặc định `label:codex-demo`. Lần đầu lấy tất cả email khớp query; có thể thêm `newer_than:7d` để giới hạn dữ liệu.
- `interval_seconds`: chu kỳ kiểm tra.
- `timezone`: múi giờ chia sổ, mặc định `Asia/Ho_Chi_Minh`.
- `rules`: mỗi rule có `category`, `keywords` và tùy chọn `senders`. Một từ khóa bất kỳ phải khớp và một người gửi bất kỳ phải khớp nếu trường tương ứng có giá trị. So khớp chuỗi con, không phân biệt hoa thường, có phân biệt dấu tiếng Việt. Một email có thể vào nhiều nhóm.
- `unmatched_category`: nhóm cho email không khớp; đặt `null` để bỏ qua.

Ví dụ:

```json
{"category": "Báo cáo", "keywords": ["báo cáo", "hạn chót"], "senders": ["@example.gov.vn"]}
```

Rules mới áp dụng cho email chưa xử lý; MVP chưa hỗ trợ phân loại lại ghi chép cũ. ID nguồn là khóa chống trùng; hai email khác ID có cùng nội dung vẫn được ghi riêng. Database là nguồn để dựng lại Markdown; chỉnh sửa Markdown bằng tay sẽ bị ghi đè trong lượt tiếp theo. Sao lưu toàn bộ `.local/` và bảo vệ dữ liệu vì email/ghi chép có thể chứa thông tin nội bộ.

## Tóm tắt tiết kiệm

Mặc định `summary.mode = "extractive"`: bỏ một số chữ ký và trích dẫn phổ biến rồi lấy tối đa `max_chars` ký tự đầu. **Đây là trích đoạn, không phải tóm tắt ngữ nghĩa**; có thể bỏ sót thời hạn nằm cuối thư. Loại chữ ký/trích dẫn là heuristic, cần xem bản gốc khi ra quyết định.

Để bật tóm tắt AI, cấu hình:

```json
{"mode": "openai", "model": "gpt-4o-mini", "max_input_chars": 12000}
```

Đặt `OPENAI_API_KEY` qua cơ chế secrets của máy triển khai, không lưu vào repository. Chế độ này gửi tiêu đề và tối đa `max_input_chars` ký tự nội dung đến OpenAI; chỉ bật khi khách cho phép xử lý dữ liệu qua nhà cung cấp đó. Email có thể dài hơn giới hạn nên tóm tắt không bao quát toàn bộ. Chỉ email qua rules và chưa có trong SQLite được tóm tắt; kết quả được lưu để tránh gọi lại. Không có quyền thao tác công cụ được cấp cho mô hình.

## Mạng cần thiết

- Gmail: `gmail.googleapis.com`
- OAuth: `accounts.google.com`, `oauth2.googleapis.com`
- AI tùy chọn: `api.openai.com`

TLS được xác minh mặc định. Không cần API key để chạy demo/extractive. Việc có domain trong cấu hình không đồng nghĩa OAuth/API đã hoạt động.

## Mở rộng website

Module Gmail trả các trường `id`, `sender`, `subject`, `received_at`, `body`. Module website tương lai có thể trả cấu trúc tương tự rồi gọi `process(..., source="web")`; cần bổ sung link nguồn website trước khi dùng thực tế. Không cần OAuth nếu nguồn công khai.

## Tình trạng kiểm chứng

Đã chạy demo và kiểm thử tự động cho phân loại, MIME/HTML, chống xử lý trùng, chia ngày theo múi giờ, link Gmail và khả năng thử lại khi tóm tắt lỗi. Đã kiểm thử API quản trị và OAuth giả lập, lưu cấu hình/lịch chạy; đã thử trình duyệt thật cho đăng nhập, demo, tìm kiếm, tải file, thêm/xóa rules và lưu cài đặt trên desktop/mobile. Chưa kiểm chứng OAuth với Google, Gmail thật hoặc OpenAI thật vì chưa có credentials. Không coi demo là bằng chứng kết nối tài khoản đã hoạt động.
