# Thử Sổ ghi chép trên macOS

Bản dành cho khách thử có **hai cách mở**. Nên dùng gói Docker Desktop với `Mo-So-Ghi-Chep-Mac.command`: cùng luồng xử lý với Windows, đã có Poppler trong container để cắt trang PDF scan gửi OCR qua DeepSeek. Bản `.app` độc lập được build riêng cho Mac Intel và Apple Silicon; hãy coi là bản thử nghiệm, vì PDF scan của `.app` còn cần Poppler trên Mac. Cả hai cách đều dùng giao diện tại `localhost:8080`, nhưng **dữ liệu ở hai vị trí khác nhau**; đừng chạy cả hai cùng lúc.

## Cách A — Docker Desktop, khuyến nghị để thử đầy đủ

1. Kiểm tra chip trong **Apple menu  → About This Mac**. Cài [Docker Desktop cho Mac](https://www.docker.com/products/docker-desktop/) đúng loại Intel hoặc Apple Silicon; mở Docker Desktop và chờ engine chạy. Không cần cài Python hay Poppler trên Mac.
2. Mở [nhánh thử](https://github.com/Anhvu210103/Codex_tool/tree/codex/windows-partner-test), chọn **Code → Download ZIP**, giải nén vào thư mục cố định, ví dụ `~/Documents/SoGhiChep`. Mở thư mục có `compose.yml`, `Dockerfile` và `Mo-So-Ghi-Chep-Mac.command`.
3. Trong Finder, bấm đúp `Mo-So-Ghi-Chep-Mac.command`. Nếu macOS chặn file tải về, bấm chuột phải vào file → **Open / Mở** → xác nhận mở; chỉ xác nhận khi ZIP lấy từ repo tin cậy. Không tắt Gatekeeper. Terminal sẽ hiện quá trình Docker tải/dựng image; lần đầu có thể mất vài phút. Khi xong, trình duyệt mở `http://localhost:8080`.
4. Tạo mật khẩu quản trị ít nhất 12 ký tự. Những lần sau mở Docker Desktop rồi bấm lại file `.command`. Dữ liệu nằm trong `.local/` cạnh file mở; thư mục nhận PDF là `inbox/` cùng chỗ. Giữ cả thư mục này khi cập nhật.
5. Muốn dừng: mở Terminal trong thư mục tool và chạy `docker compose down`. Đóng tab trình duyệt không dừng tool; máy ngủ/tắt thì lịch tự động ngừng. Muốn kiểm tra lỗi: `docker compose ps`, `docker compose logs --tail=100 mailnotes` và `http://localhost:8080/health`.

## Cách B — tải `.app` độc lập để thử giao diện

Vào [Actions → Build macOS test app](https://github.com/Anhvu210103/Codex_tool/actions/workflows/build-macos.yml), mở lượt chạy **thành công** mới nhất của nhánh thử. Ở **Artifacts**, tải `SoGhiChep-macOS-AppleSilicon` cho M1/M2/M3/M4 hoặc `SoGhiChep-macOS-Intel` cho Mac Intel. Giải nén ZIP GitHub, giải nén tiếp `SoGhiChep-macOS-...zip`, kéo `SoGhiChep.app` vào Applications. Bản thử chưa ký Developer ID/notarize: nếu bị chặn, dùng chuột phải → **Open** hoặc cho phép ở **System Settings → Privacy & Security**, không tắt Gatekeeper.

App tự mở web và lưu dữ liệu ở `~/Library/Application Support/SoGhiChep/`. Để thử OCR PDF scan với `.app`, Mac cần Poppler (`pdftoppm`) có thể cài bằng Homebrew: `brew install poppler`. Nếu không có Poppler, thử PDF có chữ trước hoặc dùng cách A. Bản `.app` không tự đồng bộ dữ liệu với cách A. Đóng app bằng nút **Tắt tool** trong giao diện; đóng tab không tắt dịch vụ.

## Thiết lập và thử tài liệu

1. Vào **Cài đặt → Nội dung & chi phí**; lưu DeepSeek API key và tích đồng ý gửi dữ liệu cho AI. Không gửi key qua chat. Vào **Nhóm tài liệu**, sửa/tạo nhóm rồi lưu.
2. Vào **Sổ ghi chép**, chọn một PDF có thể bôi đen chữ, bấm **Đọc & ghi vào sổ**. Chọn nguồn **PDF tải lên** để xem ghi chú, file `.md` theo nhóm và chi phí token. Thử lại file cũ có thể phát sinh phí nếu ô **Xử lý lại PDF đã có** còn tích.
3. Thử một PDF scan. Bật **Dùng OCR qua DeepSeek cho PDF scan** trong Cài đặt, lưu rồi nhập PDF. Đối chiếu kết quả với bản gốc, nhất là số hiệu và ngày tháng. OCR có thể phát sinh phí.
4. Nếu website không tự tải, đặt PDF vào `inbox/` của cách A, chờ file chép xong ít nhất 3 giây rồi bấm **Cài đặt → Thư mục nhận PDF thủ công → Quét thư mục ngay**. Chọn nguồn **Thư mục nhận PDF** để kiểm tra. PDF đã xử lý sẽ chuyển vào `inbox/Da-xu-ly`.
5. Muốn thử Gmail bằng thao tác trình duyệt, dùng **Google Chrome** trên Mac. Trong Cài đặt tải tiện ích, giải nén, mở `chrome://extensions`, bật Developer mode và **Load unpacked** từ thư mục có `manifest.json`. Tạo mã ghép nối trong tool; trong tiện ích nhập `http://localhost:8080` và mã, bấm **Lưu kết nối**. Mở Gmail đã đăng nhập, tìm `has:attachment filename:pdf`, bấm **Thử 1 thư** rồi xem **Báo cáo lần chạy** và nguồn **Gmail qua tiện ích Chrome**. Sau khi một thư ổn mới thử 20 thư và lịch 30 phút. Gmail API là một luồng riêng.

## Cập nhật và báo lỗi

Với cách A, dừng bằng `docker compose down`, sao lưu `.local/` và `inbox/`, giải nén ZIP mới vào thư mục mới, chép lại hai thư mục dữ liệu rồi bấm file `.command` mới. Với `.app`, thay app trong Applications **sau khi đã tắt tool**; giữ nguyên thư mục dữ liệu trong `Application Support`.

Khi báo lỗi, gửi phiên bản macOS và chip, cách A/B, bước đang làm, loại PDF (có chữ hay scan), kết quả mong đợi/thực tế và log/báo cáo tiện ích đã che thông tin riêng. Không gửi API key, mật khẩu, mã ghép nối, OAuth JSON hoặc tài liệu mật.
