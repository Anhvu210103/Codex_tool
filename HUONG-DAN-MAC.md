# Sổ ghi chép trên iMac/MacBook

Đây là bộ cài thử dành riêng cho macOS, chạy bằng Docker Desktop. Bắt đầu tại [Cài lần đầu](deploy/mac-install.md), sau đó đưa cho người sử dụng [Hướng dẫn hằng ngày](deploy/mac-user-guide.md). Mã nguồn nằm trên nhánh `codex/mac-customer-test`.

Cần giữ nguyên thư mục đã giải nén. `Mo-So-Ghi-Chep-Mac.command` tự mở Docker Desktop và mở tool bằng một lần bấm; khách chỉ cần đóng tab khi dùng xong. `Dung-So-Ghi-Chep-Mac.command` chỉ dùng khi muốn dừng hẳn lịch chạy. PDF khách tự tải được đặt trong `inbox/`; sổ, cấu hình và key nằm trong `.local/`. Không gửi hai thư mục này cho người khác.

Bản `.app` trong GitHub Actions là phương án thử kỹ thuật riêng, không dùng cùng thư mục dữ liệu với bản Docker. Tài liệu bàn giao khách ở đây chỉ hướng dẫn bản Docker để tránh chạy nhầm hai bản.

Nếu khách dùng Codex để hỏi hoặc kiểm tra lỗi, có thể dùng [skill Sổ ghi chép cho Mac](.agents/skills/so-ghi-chep-mac/README.md). Skill chỉ hướng dẫn vận hành; tool xử lý PDF bằng DeepSeek theo cấu hình khách đã lưu.

Người triển khai xem [kiểm tra bàn giao tại iMac](deploy/mac-handover-check.md) và [kết quả rà soát bản cài](deploy/customer-readiness-review.md) trước khi nghiệm thu.
