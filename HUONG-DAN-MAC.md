# Sổ ghi chép trên iMac/MacBook

Đây là bộ cài thử dành riêng cho macOS, chạy bằng Docker Desktop. Bắt đầu tại [Cài lần đầu](deploy/mac-install.md), sau đó đưa cho người sử dụng [Hướng dẫn hằng ngày](deploy/mac-user-guide.md). Mã nguồn nằm trên nhánh `codex/mac-customer-test`.

Cần giữ nguyên thư mục đã giải nén. `Mo-So-Ghi-Chep-Mac.command` mở tool; `Dung-So-Ghi-Chep-Mac.command` dừng tool. PDF khách tự tải được đặt trong `inbox/`; sổ, cấu hình và key nằm trong `.local/`. Không gửi hai thư mục này cho người khác.

Bản `.app` trong GitHub Actions là phương án thử kỹ thuật riêng, không dùng cùng thư mục dữ liệu với bản Docker. Tài liệu bàn giao khách ở đây chỉ hướng dẫn bản Docker để tránh chạy nhầm hai bản.
