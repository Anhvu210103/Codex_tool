# Ứng dụng bấm mở — Linux và macOS

Hai hệ điều hành dùng cùng quy trình nghiệp vụ và cấu trúc tài liệu: [chi tiết Linux/macOS](../deploy/linux-macos.md). Bản mã nguồn trên Mac có launcher `Mo-So-Ghi-Chep.command`, dùng lại cùng `.venv` và `.local` như Linux.

Ứng dụng có sẵn Python và thư viện, tự chạy dịch vụ nội bộ rồi mở trình duyệt mặc định. Không cần nhập lệnh mỗi lần dùng. Giao diện vẫn là trang quản trị trong trình duyệt, không phải cửa sổ webview riêng.

## Tải bản đóng gói trên GitHub

Trong repository → **Actions → Build desktop apps**, mở một lượt chạy thành công, kéo xuống **Artifacts** và tải bản đúng máy:

- **SoGhiChep-Linux-x86_64**: cho Linux Intel/AMD 64-bit. Giải nén artifact, cấp quyền chạy cho `SoGhiChep-x86_64.AppImage` rồi bấm mở. Có `SoGhiChep-Linux.tar.gz` làm phương án dự phòng cho máy không chạy được AppImage.
- **SoGhiChep-macOS-AppleSilicon**: cho Mac M1/M2/M3/M4 và chip Apple Silicon tương thích.
- **SoGhiChep-macOS-Intel**: cho Mac dùng CPU Intel.

Mac: giải nén artifact, mở `SoGhiChep.dmg`, kéo `SoGhiChep.app` vào Applications rồi mở. Khi CI chưa được cấp Apple secrets, DMG chỉ ký ad-hoc để kiểm thử và macOS có thể yêu cầu xác nhận trong System Settings → Privacy & Security. Khi có Developer ID và thông tin notarization, cùng workflow tự ký hardened runtime, gửi Apple kiểm tra và staple vé vào DMG. Không tắt Gatekeeper.

GitHub yêu cầu đăng nhập và quyền đọc repository để tải artifact. Có thể cần bật Actions cho repository nếu đang bị tắt. Quy trình build tự chạy khi nhánh codex/admin-web thay đổi các file app, hoặc chủ repository chọn Run workflow. Artifact chỉ có sau khi job tương ứng thành công; chưa coi bản Mac đã chạy được nếu chưa test trên Mac thật.

CI chạy kiểm thử ứng dụng, đóng gói trên từng hệ điều hành, rồi khởi động bản vừa đóng gói và kiểm tra đăng nhập, PDF chữ → Markdown/nhóm, PDF scan → Cần xem lại và tải ZIP tiện ích trước khi tải artifact lên. Linux còn khởi động và kiểm tra chính AppImage. Đây là phép thử tự động trên máy Mac của GitHub; vẫn cần thử trên iMac của khách để xác nhận phiên bản macOS, chip và quyền mở ứng dụng.

Để phát hành Mac không có cảnh báo, đặt các GitHub Actions secrets: `MACOS_CERTIFICATE_BASE64` (Developer ID Application `.p12` dạng base64), `MACOS_CERTIFICATE_PASSWORD`, `MACOS_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`. Không ghi các giá trị này vào repository hoặc gửi trong chat.

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

DeepSeek nhận chữ từ Markdown đã chuyển từ PDF. Bản scan được gửi qua Google Document AI OCR cloud nếu khách cấu hình processor và service account trong Cài đặt; nếu chưa cấu hình hoặc OCR thất bại thì vào Cần xem lại. Không cần cài Tesseract hay Poppler. PDF có chữ, phân loại và ghi sổ đã được tích hợp. Chứng chỉ CA công khai được đóng gói, giữ TLS verification; SSL_CERT_FILE do người dùng cấu hình được tôn trọng.

## Build cho người phát triển

Chạy trên đúng hệ điều hành/kiến trúc đích:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python packaging/build.py
.venv/bin/python packaging/smoke_app.py
```

Linux tạo `dist/SoGhiChep`, sau đó `packaging/package_linux.py` tạo AppImage bằng appimagetool và runtime đều đã kiểm tra SHA-256. macOS tạo `dist/SoGhiChep.app`, sau đó `packaging/package_macos.py` tạo và kiểm tra `dist/SoGhiChep.dmg`. Không cross-build Mac từ Linux. CI dùng Ubuntu 22.04 để có nền glibc cũ hơn; bản Linux build tại môi trường cloud hiện tại chỉ được kiểm chứng trên chính môi trường đó, không cam kết chạy mọi distro/CPU. OAuth Gmail thật, DeepSeek thật và bản macOS vẫn cần kiểm thử trên máy đích có credentials hợp lệ.

Triển khai máy chủ bằng Docker là lựa chọn riêng, xem [hướng dẫn Docker](../deploy/docker.md). Docker không thay thế DMG trên máy khách vì không mở trực tiếp Finder và cần Docker Desktop.
