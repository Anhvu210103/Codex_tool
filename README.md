# Sổ ghi chép cho khách dùng Mac · Powered by TCOM

Đây là nhánh **`codex/mac-customer-test`** dành để cài thử trên iMac/MacBook bằng Docker Desktop. PDF khách tự tải được đặt trong `inbox/`; tool dùng DeepSeek để phân nhóm, viết nội dung ngắn và lưu Markdown vào sổ. Gmail là nguồn bổ sung sau khi luồng thư mục đã ổn.

- [Bắt đầu tại đây — bộ hướng dẫn Mac](HUONG-DAN-MAC.md)
- [Cài lần đầu và bàn giao](deploy/mac-install.md)
- [Hướng dẫn khách sử dụng hằng ngày](deploy/mac-user-guide.md)

Trong Finder, bấm `Mo-So-Ghi-Chep-Mac.command` để mở và `Dung-So-Ghi-Chep-Mac.command` để dừng. Lần đầu cần cài Docker Desktop; tool sẽ yêu cầu tạo mật khẩu quản trị. Dữ liệu và key nằm trong `.local/` cạnh hai file này. Không đưa `.local/`, `inbox/`, API key hoặc token vào ZIP gửi khách.

Bản `.app` build trên macOS là bản thử kỹ thuật riêng, lưu dữ liệu ở chỗ khác. Không chạy đồng thời `.app` và bản Docker. Hướng dẫn bàn giao trên nhánh này chỉ áp dụng cho Docker Desktop.

PDF scan chỉ được OCR khi đã bật **Dùng OCR qua DeepSeek cho PDF scan** trong Cài đặt, có API key và đồng ý gửi dữ liệu. Chất lượng OCR phải đối chiếu PDF gốc. Nếu API DeepSeek không nhận ảnh, tài liệu sẽ vào **Cần xem lại**. Tiền/token trên giao diện là ước tính.

Nhà phát triển có thể chạy kiểm thử bằng `python -m unittest discover -s tests -q`; tài liệu về các hệ điều hành khác vẫn ở các nhánh tương ứng. Mac Intel và Apple Silicon cùng dùng `compose.yml` này vì Docker Desktop tự chọn image đúng kiến trúc.
