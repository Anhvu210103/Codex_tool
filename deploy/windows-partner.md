# Hướng dẫn dùng Sổ ghi chép trên Windows

Đây là bản thử `codex/windows-partner-test` chạy bằng Docker Desktop, **chưa phải file `.exe` độc lập**. Tool nhận PDF, trích chữ, dùng DeepSeek phân nhóm và tóm tắt, rồi ghi vào sổ. Nên thử **một PDF có thể bôi đen/copy chữ trước**, kiểm tra kết quả, sau đó mới thử nhiều file, PDF scan hoặc lịch Gmail.

## Cài lần đầu

1. Cài [Docker Desktop](https://www.docker.com/products/docker-desktop/) cho Windows 10/11, mở ứng dụng và đợi **Engine running**. Nếu Docker yêu cầu WSL 2 hoặc khởi động lại Windows, hoàn tất bước đó trước. Không cần cài Python.
2. Mở [nhánh Windows để thử](https://github.com/Anhvu210103/Codex_tool/tree/codex/windows-partner-test), bấm **Code → Download ZIP**. Giải nén vào một thư mục cố định, ví dụ `D:\Tcom_AI\Codex_tool`. Mở tới thư mục có đồng thời `compose.yml`, `Dockerfile` và `Mo-So-Ghi-Chep-Windows.cmd`. Giữ nguyên toàn bộ thư mục; đừng chỉ chép file `.cmd`.
3. Bấm đúp **`Mo-So-Ghi-Chep-Windows.cmd`**. Lượt đầu Docker tải và dựng image nên có thể mất vài phút. Giữ cửa sổ lệnh mở đến khi trình duyệt hiện `http://localhost:8080`. Nếu trình duyệt không tự mở, nhập địa chỉ đó vào thanh địa chỉ Chrome/Edge.
4. Trang đầu tiên yêu cầu **Tạo mật khẩu quản trị**. Tự đặt mật khẩu ít nhất 12 ký tự và lưu ở nơi riêng. Không có mật khẩu mẫu. Những lần sau: mở Docker Desktop, bấm lại file `.cmd` rồi đăng nhập. Không gửi mật khẩu hay API key cho người hỗ trợ.

Tool chỉ công bố cổng 8080 trên máy này. Nếu cổng bị ứng dụng khác chiếm, Docker sẽ báo lỗi; dừng ứng dụng đang dùng cổng rồi chạy lại. Đóng tab trình duyệt **không** dừng lịch đã bật. Muốn dừng hẳn: mở thư mục tool trong File Explorer, gõ `powershell` vào thanh địa chỉ rồi Enter, chạy `docker compose down`. Lần sau bấm lại file `.cmd`.

## Thiết lập để dùng

Trên **Tổng quan**, nút **Thư mục PDF** chỉ vị trí `inbox` trên Windows và nút **Quét thư mục** bắt đầu xử lý ngay. Trình duyệt trong Docker không thể tự mở File Explorer của máy khách.

1. Vào **Cài đặt**, mở mục **Nội dung & chi phí**. Dán **DeepSeek API key** vào ô tương ứng, bấm **Lưu key riêng**. Tích ô đồng ý gửi dữ liệu PDF cho dịch vụ AI, rồi bấm **Lưu cài đặt**. Đơn giá token đã điền sẵn; tiền hiển thị trong tool là **ước tính** theo số token trả về, đối chiếu hóa đơn DeepSeek khi cần.
2. Vào **Nhóm tài liệu**. Có thể bấm **Thêm nhóm mẫu cơ quan nhà nước**, sửa tên và mô tả cho đúng nghiệp vụ của khách rồi bấm **Lưu nhóm**. AI có thể gán một tài liệu vào nhiều nhóm. Kết quả chưa đủ rõ vào nhóm **Cần xem lại**; người dùng có thể sửa nhóm trong sổ.
3. Vào **Sổ ghi chép**, chọn một PDF có thể bôi đen chữ, bấm **Đọc & ghi vào sổ**. Chờ thông báo xử lý xong, vào **Tổng quan** xem số tài liệu và chi phí, rồi vào **Sổ ghi chép** xem nhóm, nội dung ngắn và đường dẫn file Markdown (`.md`). Chọn đúng nguồn **PDF tải lên** nếu bộ lọc nguồn đang bật. Thử lại cùng PDF có thể tốn thêm phí vì ô **Xử lý lại PDF đã có theo cấu hình mới** được tích sẵn; bỏ tích nếu chỉ muốn kiểm tra chống trùng.
4. Thử luồng nhập thủ công: chép PDF vào thư mục `inbox` nằm cạnh file `.cmd`. Đợi file chép xong và thêm ít nhất 3 giây. Trong **Cài đặt → Thư mục nhận PDF thủ công**, bấm **Quét thư mục ngay**. Chọn nguồn **Thư mục nhận PDF** trên Tổng quan hoặc Sổ ghi chép để thấy kết quả. PDF thành công chuyển sang `inbox\Da-xu-ly`; PDF lỗi còn trong `inbox` để sửa/thử lại. Muốn tự quét, tích **Tự quét thư mục theo chu kỳ đã đặt** rồi lưu cài đặt. Đây là phương án dự phòng khi trang nguồn không thể tự tải PDF.
5. Thử một PDF scan chỉ có ảnh. Trong **Cài đặt → Nguồn & lịch chạy**, bật **Dùng OCR qua DeepSeek cho PDF scan** rồi lưu. Xem lại chữ trích và nội dung ngắn với bản gốc, nhất là số hiệu, ngày tháng và tên cơ quan. OCR qua API có thể phát sinh phí và không bảo đảm nhận đúng mọi ký tự.

Nếu chỉ muốn kiểm tra phân loại, tóm tắt và lưu Markdown thì hoàn tất tới bước 4 là đủ. Phần Gmail bên dưới dùng để thử tự lấy tài liệu; nó không bắt buộc cho luồng thư mục.

## Thử tiện ích Chrome thao tác Gmail

Tiện ích bấm trên giao diện Gmail mà người dùng đang đăng nhập trong Chrome. Hãy làm từng bước:

1. Trong **Cài đặt**, mở mục **Tiện ích Chrome — AI thao tác Gmail**, bấm **Tải tiện ích Chrome**. Giải nén ZIP vào thư mục cố định, ví dụ `D:\Tcom_AI\gmail-extension`. Mở `chrome://extensions`, bật **Developer mode / Chế độ dành cho nhà phát triển**, bấm **Load unpacked / Tải tiện ích đã giải nén** và chọn đúng thư mục chứa `manifest.json`. Ghi lại số phiên bản hiển thị trên thẻ tiện ích.
2. Quay lại mục **Tiện ích Chrome — AI thao tác Gmail**, bấm **Tạo / đổi mã ghép nối** và sao chép mã mới. Bấm biểu tượng mảnh ghép 🧩 trên Chrome, mở **Sổ ghi chép — AI Gmail**. Trong phần **Kết nối với tool**, điền địa chỉ `http://localhost:8080` và mã vừa tạo, rồi bấm **Lưu kết nối**. Mã ghép nối khác mật khẩu quản trị; không gửi mã cho người khác.
3. Mở Gmail đã đăng nhập **trong chính Chrome này**, tìm `has:attachment filename:pdf`, để trang kết quả mở. Mở tiện ích, bấm **Thử 1 thư**. Giữ Chrome và tool đang chạy, chờ báo cáo cuối cùng. Kiểm tra ở **Sổ ghi chép**, chọn nguồn **Gmail qua tiện ích Chrome**. Một thư có nhiều PDF phải cho ra nhiều tài liệu tương ứng.
4. Nếu một thư chạy trọn vẹn, bấm **Xử lý 20 thư đang hiện**. Đối chiếu số thư, số PDF mới, PDF đã có và PDF lỗi trong **Báo cáo lần chạy**. Chạy lại cùng trang để kiểm tra tài liệu đã có không bị phân loại và tính phí AI thêm. Nếu báo cáo dừng sớm, sao chép toàn bộ báo cáo để xử lý lỗi; đừng kết luận chỉ từ số mail đã mở.
5. Sau khi thử tay ổn, bật **Tự kiểm tra mỗi 30 phút** trong tiện ích. Khi bật, tiện ích bắt đầu kiểm tra ngay rồi chạy theo lịch khi Chrome và tool còn mở. Bộ lọc Gmail đang dùng phải cho đúng tập thư muốn theo dõi. Nếu chỉ muốn thư chưa đọc, chọn bộ lọc đó trong Gmail và kiểm tra lại trang kết quả trước khi chạy. Không bật đồng thời lịch tiện ích và lịch Gmail API cho cùng nguồn nếu chưa cần.

Trên Windows, tiện ích thử lấy PDF theo URL sau khi Chrome tải. Nếu Gmail không cho đọc lại URL, tiện ích có thể yêu cầu **Đưa PDF vào sổ bằng tay**. Khi đó chọn PDF đã tải hoặc đưa vào `inbox` để tool xử lý; đây là phương án dự phòng có chủ đích. Luồng Chrome trên Windows cần được thử bằng tài khoản Gmail và PDF thực tế của đối tác trước khi giao chạy tự động thường xuyên.

## Tùy chọn: dùng Gmail API

Gmail API là một cách lấy thư khác, chạy theo lịch trong container và không cần để Chrome mở. Trong Google Cloud, tạo project, bật Gmail API, cấu hình màn hình đồng ý OAuth và thêm địa chỉ Gmail thử nghiệm vào **Test users** nếu ứng dụng còn ở chế độ Testing. Tạo OAuth client loại **Web application**. Trong tool mở **Cài đặt → Kết nối Gmail**, sao chép **Authorized redirect URI** mà tool hiển thị (cổng mặc định là `http://localhost:8080/oauth/callback`) vào OAuth client. Tải file client JSON từ Google, tải lên tool, lưu cấu hình rồi bấm **Kết nối Gmail** và cấp quyền đọc. Đặt bộ lọc và lịch ở **Nguồn & lịch chạy**, thử **Quét Gmail API ngay** trên Tổng quan. Không gửi client JSON hoặc token cho người hỗ trợ.

## Tài liệu, cập nhật và kiểm tra lỗi

- Dữ liệu, sổ, cấu hình và token nằm ở `.local` cạnh file `.cmd`; PDF đưa vào ở `inbox`. Mỗi nguồn có thư mục riêng. PDF gốc giữ một bản trong `files/`; bản theo nhóm là file `.md` ở `Theo-nhom/` hoặc `Can-xem-lai/`. Đường dẫn trong sổ là **đường dẫn trong container** (`/app/.local/...`); trên Windows, thay `/app/.local/` bằng đường dẫn tới `.local\` trong thư mục tool để mở bằng Explorer.
- Để cập nhật bản ZIP: chạy `docker compose down` trong thư mục cũ; sao lưu `.local` và `inbox`. Giải nén ZIP mới vào **thư mục mới**, chép nguyên `.local` và `inbox` từ thư mục cũ sang thư mục mới, rồi bấm file `.cmd` ở thư mục mới. Kiểm tra sổ cũ còn đủ trước khi xóa bản cũ. Nếu đã clone bằng Git, chạy `git pull origin codex/windows-partner-test` trong đúng thư mục Git rồi bấm lại file `.cmd`.
- Sau khi cập nhật tiện ích, tải ZIP mới và **Load unpacked** từ thư mục mới, hoặc thay đúng thư mục Chrome đang nạp rồi bấm **Reload**. Chrome Reload không tự thay một thư mục cũ trong Downloads.
- Trạng thái container: `docker compose ps`. Xem lỗi: `docker compose logs --tail=100 mailnotes`. Kiểm tra web: `http://localhost:8080/health`. Nếu trang web trắng, tải lại bằng Ctrl+Shift+R sau khi container đã chạy.

Bản Windows này dùng Docker Desktop; chưa phải ứng dụng `.exe` độc lập. PDF có chữ được trích trên máy chủ container. Với PDF scan, bật OCR qua DeepSeek nếu cần; kết quả OCR cần đối chiếu bản gốc và có thể phát sinh phí. Không cần cấu hình OCR cục bộ.

## Khi gặp lỗi, gửi thông tin gì?

| Hiện tượng | Cách kiểm tra trước |
| --- | --- |
| Bấm file `.cmd` nhưng web không mở | Xem Docker Desktop đã báo **Engine running** chưa; chạy `docker compose ps` và mở `http://localhost:8080/health`. Nếu cổng 8080 bận, dừng ứng dụng đang chiếm cổng. |
| Web trắng hoặc không thấy kết quả mới | Đợi container chạy xong, bấm Ctrl+Shift+R; kiểm tra bộ lọc **nguồn** và khoảng ngày trên Tổng quan/Sổ ghi chép. |
| PDF trong `inbox` chưa được quét | Chép file trực tiếp vào `inbox`, đợi ghi xong ít nhất 3 giây, bấm **Quét thư mục ngay**; xem file đã chuyển vào `Da-xu-ly` chưa. |
| PDF scan không có chữ hoặc tóm tắt sai | Bật OCR qua DeepSeek, chạy lại tài liệu và đối chiếu PDF gốc; ghi rõ trang/số hiệu nhận sai. |
| Tiện ích vẫn hiển thị phiên bản cũ | Kiểm tra đường dẫn ở `chrome://extensions`; nạp đúng thư mục mới có `manifest.json`, rồi bấm **Reload**. |
| Gmail mở được PDF nhưng sổ chưa có tài liệu | Mở **Báo cáo lần chạy** của tiện ích, tìm các bước tải và nhập PDF; kiểm tra bộ lọc nguồn **Gmail qua tiện ích Chrome**. Nếu tiện ích yêu cầu chọn file, dùng **Đưa PDF vào sổ bằng tay** hoặc `inbox`. |

Để gửi lỗi cho người triển khai, mở PowerShell ở thư mục tool và chạy `docker compose logs --tail=100 mailnotes`. Gửi **thời điểm, bước đang làm, kết quả mong đợi/kết quả thực tế, báo cáo tiện ích và log**; nếu có thể ghi số PDF trong một thư và loại PDF (có chữ hay scan). Che địa chỉ cá nhân, tên tài liệu nhạy cảm; **không gửi API key, mật khẩu, mã ghép nối, OAuth JSON hoặc token**.

## Checklist nghiệm thu bản thử

- [ ] Mở bằng file `.cmd`, đăng nhập được và giữ lại dữ liệu sau khi dừng/mở lại Docker.
- [ ] Một PDF có chữ tạo được nội dung ngắn, nhóm đúng và file `.md` trên máy; số token và tiền ước tính xuất hiện.
- [ ] Một PDF scan được OCR qua DeepSeek, nội dung cần thiết đối chiếu được với bản gốc.
- [ ] Nhiều PDF trong một thư Gmail được ghi riêng; báo cáo thể hiện đúng số thành công, đã có và lỗi.
- [ ] Chạy lại cùng dữ liệu không tạo mục trùng hoặc tốn AI cho tài liệu đã xử lý.
- [ ] Khi Gmail không tự tải được, đặt PDF vào `inbox` vẫn xử lý và lưu được.

Ghi lại phiên bản Windows, Docker Desktop, Chrome và tiện ích; số file đã thử, loại file, số thành công/lỗi, nhóm phân loại sai và ảnh màn hình thông báo lỗi (nếu có). Những thông tin đó đủ để tái hiện và sửa lỗi mà không cần gửi tài liệu mật.
