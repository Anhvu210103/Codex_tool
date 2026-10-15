# Ứng dụng bấm mở — Linux và macOS

Ứng dụng có sẵn Python và thư viện, tự chạy dịch vụ nội bộ rồi mở trình duyệt mặc định. Không cần nhập lệnh mỗi lần dùng. Giao diện vẫn là trang quản trị trong trình duyệt, không phải cửa sổ webview riêng.

## Tải bản đóng gói trên GitHub

Trong repository → **Actions → Build desktop apps**, mở một lượt chạy thành công, kéo xuống **Artifacts** và tải bản đúng máy:

- **SoGhiChep-Linux-x86_64**: cho Linux Intel/AMD 64-bit. Giải nén ZIP tải từ GitHub, rồi giải nén `SoGhiChep-Linux.tar.gz`. Bấm file `SoGhiChep` bên trong. Nếu hệ thống hỏi quyền chạy: Properties → Permissions → Allow executing file as program. Lần đầu app tự thêm mục **Sổ ghi chép** vào danh sách ứng dụng; lần sau tìm theo tên để mở. Giữ file app ở vị trí cố định, đừng xóa sau khi thêm vào menu.
- **SoGhiChep-macOS-AppleSilicon**: cho Mac M1/M2/M3/M4 và chip Apple Silicon tương thích.
- **SoGhiChep-macOS-Intel**: cho Mac dùng CPU Intel.

Mac: giải nén ZIP artifact rồi ZIP chứa app, kéo `SoGhiChep.app` vào Applications và mở. Bản build thử chưa có chứng chỉ Developer ID/notarization. macOS có thể yêu cầu mở bằng menu chuột phải/Open hoặc cho phép trong System Settings → Privacy & Security; chỉ làm với bản do bạn tự build/tải từ repository tin cậy. Không tắt Gatekeeper hoặc xác minh hệ thống. Ký và notarize bằng tài khoản Apple Developer là bước riêng trước khi phát hành chính thức cho khách.

GitHub yêu cầu đăng nhập và quyền đọc repository để tải artifact. Có thể cần bật Actions cho repository nếu đang bị tắt. Quy trình build tự chạy khi nhánh codex/admin-web thay đổi các file app, hoặc chủ repository chọn Run workflow. Artifact chỉ có sau khi job tương ứng thành công; chưa coi bản Mac đã chạy được nếu chưa test trên Mac thật.

## Dùng bản mã nguồn đã cài trên máy bạn

Với repository đã có `.venv` và thư viện như các bước trước: cập nhật mã nguồn một lần, dừng phiên Terminal cũ bằng Ctrl+C. Sau đó dùng file **Mo-So-Ghi-Chep.sh** bằng trình quản lý file (Run as a Program / Chạy như chương trình). Nó dùng lại dữ liệu `.local/` hiện có và thêm mục Sổ ghi chép vào danh sách ứng dụng Linux. Không cần chạy lại lệnh Python mỗi lần.

Không chạy đồng thời phiên web/CLI cũ và launcher dùng cùng dữ liệu. Launcher kiểm soát việc mở lặp lại của chính nó, không quản lý các phiên CLI do người dùng chạy riêng.

## Mở / tắt

- Bấm app: mở trình duyệt khi dịch vụ sẵn sàng. Nếu app đã chạy, lần bấm tiếp theo chỉ mở lại trang, không thêm scheduler.
- Đóng tab trình duyệt: tool vẫn chạy nền và kiểm tra theo lịch đã bật.
- Để tắt hẳn: đăng nhập → **Tắt tool** ở thanh bên. Nếu đang xử lý tài liệu, đợi xong rồi tắt. Mở lại bằng biểu tượng app.
- Mặc định dùng localhost:8080; nếu bận, app chọn cổng trống 8081–8090 và nhớ cổng đó. Gmail OAuth cần redirect URI khớp đúng cổng hiển thị ở Cài đặt; nếu cổng thay đổi, cập nhật OAuth client tương ứng.
- App chỉ nghe loopback, không tự mở cổng ra mạng. Đây là ứng dụng một người dùng trên máy local, không thay thế triển khai máy chủ cho nhiều người.
- Máy ngủ/tắt sẽ dừng kiểm tra thư; sau khi bật lại cần mở app. App chưa tự khởi động khi đăng nhập hệ điều hành.

## Dữ liệu không nằm trong app

- Bản app Linux: `~/.local/share/so-ghi-chep/` (hoặc `$XDG_DATA_HOME/so-ghi-chep/`).
- Bản app Mac: `~/Library/Application Support/SoGhiChep/`.
- Launcher mã nguồn: `.local/` trong repository, giữ nguyên dữ liệu cũ.

Thay file executable hoặc `.app` không xóa dữ liệu. Nếu chuyển từ source sang app đóng gói, dừng cả hai, sao lưu và **chép nội dung `.local/` vào thư mục dữ liệu app tương ứng** bằng trình quản lý file, giữ cấu trúc thư mục. Không ghi đè thư mục đã có dữ liệu khác khi chưa sao lưu. Không chép `.venv/` vào đó. Linux bật Show Hidden Files (Ctrl+H) để thấy `.local`; Mac dùng Finder → Go → Go to Folder để mở đường dẫn.

Có thể dùng MAILNOTES_DATA_DIR để chọn thư mục dữ liệu riêng khi triển khai có quản lý. Không gửi data/token/key qua chat. Nhật ký khởi động nằm ở `admin/desktop.log` trong thư mục dữ liệu; chỉ chia sẻ lỗi đã loại bỏ thông tin riêng.

OCR scan vẫn là tính năng tùy chọn cần Poppler + Tesseract với vie+eng trên máy; bản app không cài công cụ hệ thống bằng quyền admin. PDF có chữ, phân loại và ghi sổ đã được tích hợp. Chứng chỉ CA công khai được đóng gói, giữ TLS verification; SSL_CERT_FILE do người dùng cấu hình được tôn trọng.

## Build cho người phát triển

Chạy trên đúng hệ điều hành/kiến trúc đích:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python packaging/build.py
```

Linux tạo `dist/SoGhiChep`; macOS tạo `dist/SoGhiChep.app`. Không cross-build Mac từ Linux. CI dùng Ubuntu 22.04 để có nền glibc cũ hơn; bản Linux build tại môi trường cloud hiện tại chỉ được kiểm chứng trên chính môi trường đó, không cam kết chạy mọi distro/CPU. PDF scan tiếng Việt, OAuth Gmail thật, DeepSeek thật và bản macOS vẫn cần kiểm thử trên máy đích có credentials hợp lệ.
