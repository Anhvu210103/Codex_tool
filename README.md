# Mailnotes — Gmail → sổ ghi chép theo ngày

## Chạy cục bộ bằng Docker Compose

Yêu cầu Docker Desktop đang chạy. Từ thư mục `Codex_tool`, tạo file `.env` từ mẫu và thay mật khẩu bằng giá trị riêng dài ít nhất 12 ký tự:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build -d
```

Mở [http://localhost:8080](http://localhost:8080). Dữ liệu, cấu hình, OAuth token và API key được lưu persistent trong thư mục `.local` của project. Mật khẩu trong `MAILNOTES_ADMIN_PASSWORD` chỉ dùng để bootstrap khi `.local/admin/password.json` chưa tồn tại; sau đó có thể đổi mật khẩu trên web và xóa biến này khỏi `.env`.

### Thư mục đưa PDF cho AI xử lý

Tạo hoặc dùng thư mục sau trên máy Windows:

```text
D:\Tcom_AI\Codex_tool\inbox
```

Chép các file PDF cần đọc vào thư mục này. Container sẽ thấy cùng thư mục tại
`/app/inbox`; trong giao diện, vào **Cài đặt → Thư mục nhận PDF thủ công** rồi
bấm **Quét thư mục ngay**, hoặc bật tự quét theo chu kỳ. File hợp lệ sẽ được
đọc, trích chữ, phân loại/tóm tắt theo cấu hình, rồi chuyển vào:

```text
D:\Tcom_AI\Codex_tool\inbox\Da-xu-ly
```

File scan không có lớp chữ hoặc file lỗi sẽ được giữ lại/đánh dấu cần xem lại.
PDF phải ổn định ít nhất 3 giây trước khi quét; giới hạn kích thước là 20 MB.

Kiểm tra trạng thái hoặc dừng ứng dụng:

```powershell
docker compose ps
docker compose logs -f mailnotes
docker compose down
```

### Các thành phần trong cùng một file Compose

Service `mailnotes` là runtime chính và bao gồm web quản trị, scheduler Gmail API,
thư mục nhận PDF, SQLite và xử lý PDF → Markdown → DeepSeek. Chạy đúng một service
này để tránh hai process cùng xử lý một thư mục dữ liệu.

Các job one-shot dùng profile `tools`:

```powershell
# Chạy dữ liệu mẫu qua CLI
docker compose --profile tools run --rm demo

# Chạy một lượt Gmail API (cần credentials/token trong .local)
docker compose --profile tools run --rm cli-gmail

# Chạy toàn bộ test trong image
docker compose --profile tools run --rm tests
```

`cli-gmail` không được chạy đồng thời với một lượt xử lý Gmail đang chạy trên
website nếu cùng dùng thư mục `.local`.

Chrome Extension không phải Docker service: nó được load vào Chrome trên máy
người dùng và kết nối về `localhost:8080`. AI Gmail pilot (`gmail_browser_pilot`)
cũng cần Chrome/Chromium có phiên Gmail đăng nhập và cửa sổ đồ họa tương tác,
nên không thể chạy đầy đủ headless bằng Compose trên Docker Desktop Windows.
Các thành phần này tiếp tục chạy trên host và dùng service `mailnotes` trong
Compose.

MVP đọc nội dung Gmail, PDF đính kèm và PDF tải lên, phân loại theo rules, chống xử lý trùng bằng SQLite và xuất Sổ ghi chép dạng bảng Markdown theo ngày nhận email. Bảng gồm giờ nhận, tiêu đề, người gửi, phân loại, nội dung ngắn và nguồn; giờ hiển thị theo múi giờ cấu hình. Chỉ đọc Gmail, không gửi thư, không đổi nhãn hoặc đánh dấu đã đọc.

## Mở bằng app, không gõ lệnh mỗi lần

Linux và macOS dùng cùng luồng PDF → Markdown → DeepSeek → thư mục nhóm. Xem [quy trình chung và khác biệt đường dẫn Linux/macOS](deploy/linux-macos.md). Mỗi máy giữ dữ liệu riêng, chưa có đồng bộ tài liệu giữa các máy.

Có launcher **Mo-So-Ghi-Chep.sh** cho bản mã nguồn Linux đã cài và gói app tự chứa Python/thư viện cho Linux/macOS. Bấm app để tự chạy nền và mở trang quản trị. Lần bấm tiếp theo mở lại phiên đang chạy. Đăng nhập rồi dùng nút **Tắt tool** để dừng hẳn; đóng tab chỉ đóng giao diện.

Xem [cách tải app, cài và giữ dữ liệu](packaging/README.md). Bản Linux đã build và kiểm chứng chạy độc lập tại môi trường phát triển; bản Mac có quy trình build GitHub Actions riêng cho Apple Silicon/Intel, chưa khẳng định hoạt động trên máy khách trước khi có kết quả build và kiểm thử. App Mac thử nghiệm chưa ký/notarize. Dữ liệu riêng được giữ ngoài app để không mất khi cập nhật.

## Tiện ích Chrome — thử trên Gmail đã đăng nhập

Ưu tiên hoàn thiện Linux trước: [quy trình kiểm tra Linux](deploy/linux-test.md). Tiện ích 0.7.0 có lịch riêng tự kiểm tra PDF trong Gmail mỗi 30 phút khi Chrome và tool đang chạy. Người dùng chọn phạm vi quét bù, hôm nay, 7 ngày, khoảng ngày hoặc tất cả thư có PDF ngay trong popup. Thư và PDF đã xử lý được ghi nhớ; tiện ích kiểm tra hết kết quả trong giới hạn, tối đa 20 trang và 100 thư mỗi trang, mở mọi PDF trong một thư và chỉ chọn nút tải trên thanh công cụ trình xem.

Dùng **Cài đặt → Tiện ích Chrome → Tải tiện ích Chrome** để lấy ZIP. Giải nén, mở `chrome://extensions`, bật Developer mode và Load unpacked thư mục có manifest.json. Tạo mã ghép nối trong Cài đặt tool, dán mã cùng địa chỉ localhost của tool vào popup tiện ích. Bật **Tự kiểm tra Gmail mỗi 30 phút** trong tiện ích để bắt đầu ngay và lặp theo lịch, hoặc mở danh sách thư có PDF trên Gmail rồi bấm **Xử lý tối đa 20 thư đang hiện**. Lịch tự động quét bù từ lần thành công gần nhất, kiểm tra hết kết quả trong giới hạn và giữ hàng đợi lỗi qua lần chạy sau. Lịch này khác lịch Gmail API ở trang quản trị: nó cần Chrome, phiên Gmail đã đăng nhập và tool cùng chạy. Không cần Playwright; tiện ích thao tác trên trang Gmail, còn DeepSeek phân loại và tóm tắt PDF sau khi tải. Chi tiết, quyền truy cập và giới hạn: [chrome-extension/README.md](chrome-extension/README.md). Chưa kiểm chứng lịch và thao tác Gmail thật trên máy người dùng.

Nếu website không thể tự tải, dùng **Cài đặt → Thư mục nhận PDF thủ công**. Tool tạo `~/Downloads/So-Ghi-Chep-Inbox` trên Linux và macOS. Người dùng tự tải hoặc chép PDF vào đó rồi bấm **Quét thư mục ngay**, hoặc bật quét theo chu kỳ. Tool chỉ nhận file PDF hợp lệ đã ổn định ít nhất 3 giây, chống trùng SHA-256 với cả Gmail/PDF đã lưu, phân loại vào nguồn **Thư mục nhận PDF**, rồi chuyển bản gốc sang `Da-xu-ly`. File lỗi được giữ nguyên để thử lại và hiển thị trong trạng thái thư mục.

## Bản thử AI thao tác Gmail bằng trình duyệt — cách Playwright cũ

Trên máy Linux đang chạy bản mã nguồn, dùng **Mo-AI-Gmail.sh** để mở bản thử riêng. Lần đầu launcher cài `requirements-browser.txt` vào `.venv` hiện có; cần Chrome hoặc Chromium cài trên máy. Bản thử dùng hồ sơ trình duyệt riêng tại `.local/browser-gmail/profile`; người dùng đăng nhập Gmail ngay trong cửa sổ đó. Không gửi mật khẩu cho tool hay cho người hỗ trợ. Nếu Google từ chối đăng nhập bằng trình duyệt tự động, dừng bản thử và tiếp tục dùng kết nối Gmail API đã có.

Trước khi chạy, trong Cài đặt bật DeepSeek AI, lưu key và đồng ý xử lý dữ liệu. DeepSeek nhận **chữ và nhãn nút/hàng đang thấy trên Gmail**, không nhận ảnh chụp màn hình và chọn email hoặc nút PDF; mỗi lượt chọn có thể dùng token. Bản thử áp dụng bộ lọc Gmail đã lưu cộng điều kiện có PDF, thử tối đa 3 thư, tải PDF qua giao diện và ghi vào nguồn **AI thao tác** trong sổ. Tải lại cùng file sẽ xử lý lại; cache AI có thể tránh một lượt phân loại trùng. Chỉ cho phép mở thư và chọn PDF; lựa chọn gửi/xóa/lưu trữ bị chặn. Mở thư có thể khiến Gmail đánh dấu đã đọc. Bản thử không chạy theo lịch và chưa thay thế bộ kết nối Gmail API.

Đây là phép thử điều khiển trình duyệt trên Gmail, chưa phải bằng chứng hoạt động trên website cơ quan nhà nước. Đã kiểm thử lựa chọn AI, chặn nút nguy hiểm và nhận diện hàng email/nút PDF trên trang mô phỏng; chưa thử Gmail thật vì môi trường phát triển không có phiên đăng nhập của người dùng. Bản macOS đóng gói hiện chưa kèm Playwright; cần kiểm chứng bản thử trên Linux trước khi quyết định cách tích hợp cho iMac.

## PDF → Markdown → nhóm trên máy

PDF có lớp chữ được chuyển bằng pypdf thành Markdown trước khi gửi chữ cho DeepSeek. PDF scan có thể bật OCR qua DeepSeek trong **Cài đặt → Dùng OCR cho PDF scan**: Docker chỉ dùng Poppler để cắt từng trang thành ảnh, gửi ảnh Base64 lần lượt cho DeepSeek, ghép phản hồi thành Markdown rồi dùng Markdown đó cho phân nhóm/tóm tắt. Khi tắt OCR, bản scan được giữ nguyên PDF và tạo ghi chú Cần xem lại, không gọi AI để đoán nội dung. PDF vừa có chữ vừa có trang scan/trắng sẽ có cảnh báo phần chưa đọc. Chuyển Markdown là trích chữ, không cam kết giữ đúng bảng, cột và bố cục của PDF. PDF gốc giữ trong `files/`; mỗi nhóm có bản PDF và ghi chú Markdown riêng trong `Theo-nhom/<nhóm>/` hoặc `Can-xem-lai/`. Sổ ghi chép web và Markdown theo ngày hiển thị đường dẫn PDF trên máy.

Mỗi nguồn Gmail, PDF tải lên và AI thao tác có kho riêng trong thư mục dữ liệu. `files/` giữ PDF gốc, `Markdown/` giữ bản chữ, `Theo-nhom/<tên nhóm>/` chứa bản Markdown gồm tóm tắt và toàn bộ chữ trích được, `Can-xem-lai/` giữ ghi chú cần kiểm tra. Một tài liệu có nhiều nhóm có nhiều bản Markdown, dùng chung PDF gốc. Tên file/thư mục có mã ngắn để tránh trùng hoặc thoát đường dẫn. Khi sửa nhóm trong sổ, bản Markdown theo nhóm được cập nhật mà không gọi AI.

Trong Sổ ghi chép chọn nguồn rồi bấm **Mở thư mục tài liệu**, hoặc **Tải Markdown** ở từng dòng. Đường dẫn hiển thị là trên máy chạy tool. Với bản Mac đóng gói, dữ liệu mặc định trong `~/Library/Application Support/SoGhiChep/`; với mã nguồn là `.local/` trong repo. Ghi chú cũ chưa có Markdown cần bấm Đọc lại PDF một lần. Mỗi lượt lấy chữ/AI có giới hạn trang/ký tự đã cấu hình; cảnh báo chỉ rõ phần bị giới hạn. Đổi sang Markdown không làm token chữ miễn phí; cache giúp tránh gọi lại nếu nội dung và cấu hình không đổi.

## Nhóm mẫu cho cơ quan nhà nước

Bản cài mới có 14 nhóm mẫu: văn bản pháp luật, công việc cần xử lý, công văn chỉ đạo, thủ tục hành chính, kinh tế và đầu tư, tài chính và ngân sách, thuế/phí, đấu thầu, doanh nghiệp, đất đai/xây dựng, lao động/an sinh, báo cáo/thống kê, nhân sự nội bộ và thanh tra/kiểm tra. Mỗi nhóm có mô tả để DeepSeek chọn khi đọc tài liệu và từ khóa để thử chế độ miễn phí. Một tài liệu có thể vào nhiều nhóm.

Bản đã cài giữ nguyên nhóm người dùng đã lưu. Muốn bổ sung nhóm mẫu, vào **Nhóm tài liệu → Thêm nhóm mẫu cơ quan nhà nước**, xem lại mô tả rồi bấm **Lưu quy tắc**. Nút chỉ thêm nhóm còn thiếu theo tên, không xóa hoặc ghi đè nhóm riêng. Nhóm mới áp dụng cho tài liệu xử lý tiếp theo; PDF cũ có thể đọc lại nếu muốn phân loại theo nhóm mới.

## Phân loại + tóm tắt bằng DeepSeek

1. Vào **Nhóm tài liệu**, đặt tên nhóm và mô tả, bấm Lưu quy tắc. Từ khóa/người gửi chỉ dùng trong chế độ rules miễn phí.
2. Vào **Cài đặt → Nội dung & chi phí**, chọn **AI phân nhóm + tóm tắt**, nhà cung cấp **DeepSeek**, model **deepseek-chat**.
3. Xác nhận đồng ý gửi nội dung đến nhà cung cấp, nhập API key DeepSeek, bấm **Lưu key riêng** rồi **Lưu cài đặt**. Không gửi key vào chat.
4. Vào **Sổ ghi chép**, chọn PDF và bấm **Đọc & ghi vào sổ**; hoặc bật **Đọc PDF đính kèm Gmail** rồi chạy nguồn Gmail. Một tài liệu có thể thuộc nhiều nhóm.
5. Bấm **Sửa nhóm** tại dòng ghi chép khi cần điều chỉnh. Không gọi AI lại khi sửa nhóm. Có nút tải PDF gốc.

AI được gọi để OCR từng trang rồi gọi tiếp một lần để trả cả nhóm và tóm tắt, có cache và chống xử lý trùng cho bước phân tích. Không chắc chắn/nhóm lạ sẽ vào **Cần xem lại**. Kết quả OCR cần đối chiếu bản gốc và chỉ đọc tối đa 20 trang đầu. PDF quá dài bị giới hạn và có cảnh báo; không coi trích đoạn hoặc tóm tắt phần đầu là đã đọc toàn bộ tài liệu. Lần tải lại PDF đã có mặc định xử lý lại theo cấu hình mới; có thể tốn phí và thay nội dung/nhóm đã chỉnh tay. Có thể bỏ dấu chọn nếu muốn giữ bản đã xử lý.

Đã kiểm chứng với PDF có chữ thật, AI giả lập và trình duyệt thật. DeepSeek thật chưa được gọi vì chưa có API key; chất lượng phân nhóm/tóm tắt cần đối chiếu tài liệu của khách. Chế độ mẫu luôn dùng rules và trích đoạn miễn phí, không giả vờ là kết quả AI.

## Giao diện dễ đọc

Mặc định chữ nội dung 18px, màu chữ phụ có tương phản rõ, nút/ô nhập khoảng 48–50px và nhãn nhóm lớn hơn. Góc trên có **Cỡ chữ → Dễ đọc / Lớn / Rất lớn** (18/20/22px); lựa chọn được ghi nhớ trên trình duyệt, không đổi cấu hình xử lý tài liệu. Các cỡ dùng đơn vị rem để toàn bộ giao diện tăng cùng nhau.

Ghi chép gần nhất nằm trước cấu hình nguồn trên Tổng quan. Nội dung tóm tắt không còn bị nhốt trong vùng cuộn nhỏ; bảng có hàng xen kẽ, tiêu đề rõ, vùng cuộn ngang có thể focus bằng bàn phím và có hướng dẫn vuốt trên điện thoại. Điều hướng mobile xếp thành các nút thay vì chữ nhỏ phải kéo ngang. Đã kiểm tra năm màn hình ở các độ rộng 1440, 1280, 1024, 390 và 320px, gồm chế độ chữ rất lớn; các cặp màu chữ chính kiểm tra đều đạt tương phản ít nhất 4.5:1. Chưa coi đây là đánh giá khả năng tiếp cận toàn diện bằng công nghệ hỗ trợ.

## Tổng quan dùng hằng ngày

Trang Tổng quan hiển thị tiền AI hôm nay và tổng chi phí đã biết (USD ước tính), token hôm nay, tài liệu nhận hôm nay, số tài liệu Cần xem lại, trạng thái/lượt chạy gần nhất, lịch tự động và 8 ghi chép gần nhất. Bảng hướng dẫn Bắt đầu đơn giản đã bỏ. Có nút Chạy ngay, Đọc PDF, xem sổ, xem nhóm và sửa nhóm tại dòng ghi chép.

Tiền/token tổng hợp tất cả nguồn; tài liệu/nhóm tính theo nguồn đang xem (Gmail, PDF tải lên hoặc dữ liệu mẫu). Hôm nay tính theo múi giờ cấu hình. Tài liệu nhận hôm nay dùng ngày nhận, không phải ngày chạy; tiền dùng thời gian phản hồi API được ghi nhận. Tài liệu cần xem lại được đếm theo nhóm Cần xem lại, cập nhật ngay khi người dùng sửa nhóm. Chi phí chưa đủ đơn giá/usage được báo rõ, không coi là hóa đơn đầy đủ. Số liệu tự cập nhật khi trang mở, không gọi AI để tính thống kê.

## Token và tiền AI

Mở **Token & chi phí** để xem tổng token API đã báo, đầu vào/đầu ra, cache đầu vào của nhà cung cấp, cache nội bộ miễn phí, thống kê từng provider/model và 50 lượt gần nhất. Dữ liệu bắt đầu được ghi từ phiên bản này; không dựng lại usage của các lượt cũ.

Trong **Cài đặt → Nội dung & chi phí**, nhập đơn giá model hiện tại bằng **USD / 1 triệu token** cho đầu vào không cache, đầu vào cache API và đầu ra. Để trống nếu chưa biết. Tiền là **ước tính**, không phải số dư hay hóa đơn thực tế. Đơn giá được chụp tại thời điểm có phản hồi API; đổi giá không làm thay đổi chi phí lịch sử. Đổi provider/model trên UI sẽ xóa các ô đơn giá để tránh dùng nhầm giá cũ.

Lượt API có phản hồi vẫn ghi usage trước khi kiểm tra JSON, vì phản hồi không hợp lệ vẫn có thể tính phí. API không trả usage được đánh dấu chưa biết; request lỗi/timeout không có usage có thể thiếu trong thống kê. Cache nội bộ không gọi API, token/chi phí mới bằng 0. Email/PDF đã xử lý và bị bỏ qua không tạo thêm lượt thống kê. Cache đầu vào API là một khái niệm khác, vẫn có thể bị tính phí theo bảng giá nhà cung cấp.

## Chọn thư Gmail bằng nút và lịch

Trong Cài đặt → Bạn muốn đọc thư nào?, chọn **Hôm nay**, **7 ngày gần đây (tính cả hôm nay)**, **Chọn khoảng ngày** hoặc **Tất cả thư**. Hôm nay được tính theo múi giờ đã lưu và tự đổi mỗi lượt chạy, không phải 24 giờ gần nhất. Khoảng ngày bao gồm cả ngày bắt đầu và đến hết ngày kết thúc. Có thể nhập email người gửi, tên nhãn và chọn Chỉ lấy thư có PDF; để trống để không giới hạn các điều kiện đó. Thư rác/Thùng rác mặc định không lấy.

Giao diện hiển thị câu mô tả dễ đọc thay cho cú pháp tìm kiếm. Chọn PDF tự bật đọc file đính kèm. Tất cả thư có thông báo về thời gian/chi phí; thư đã xử lý vẫn được bỏ qua. Thiết lập cũ được giữ ở chế độ nâng cao khi nâng cấp; chuyển sang Hôm nay rồi lưu để dùng bộ chọn mới. Khách mới mặc định Hôm nay. Chế độ nâng cao chỉ dành cho người cần cú pháp Gmail, không kết hợp các lựa chọn đơn giản.

## PDF đính kèm Gmail — không cần tải lên thủ công

Trong Cài đặt, chọn nguồn **Gmail — email và PDF đính kèm**, bật **Tự tải và ĐỌC PDF đính kèm Gmail**, chọn thời gian/người gửi phù hợp rồi lưu và Chạy ngay/bật lịch. Tool tự lấy file qua Gmail API, chuyển phần chữ sang Markdown và phân nhóm/tóm tắt nội dung bên trong. Mỗi PDF là một ghi chép. Email không có PDF vẫn xử lý thân thư. Email có PDF không tạo ghi chép riêng cho thân thư.

Trong sổ chọn nguồn Gmail, xem tên PDF, nội dung ngắn và nhóm; có link email gốc, Tải PDF và **Đọc lại PDF**. Nút đọc lại dùng cấu hình hiện tại, có thể tốn phí và thay nội dung/nhóm đã sửa tay; cache được dùng lại nếu input/prompt không đổi. Scan không có lớp chữ được đánh dấu Cần xem lại, không được giả vờ đã đọc.

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

- `gmail_filter`: các lựa chọn đơn giản trong web, mặc định Hôm nay cho cấu hình mới.
- `gmail_query`: cú pháp Gmail chỉ dùng ở chế độ nâng cao hoặc cấu hình CLI cũ chưa có gmail_filter. Các điều kiện ngày đơn giản được tính lại mỗi lượt theo múi giờ.
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

Để bật AI qua CLI, cấu hình `classification_mode: "ai"`, `summary.mode: "openai"` (tên legacy của chế độ AI), `summary.provider: "deepseek"`, `summary.model: "deepseek-chat"`, `summary.ai_consent: true` và đặt `DEEPSEEK_API_KEY` bằng cơ chế secrets. CLI chưa có lệnh upload PDF; dùng trang web cho upload. Không đặt key trong config.json.

## Mạng cần thiết

- Gmail: `gmail.googleapis.com`
- OAuth: `accounts.google.com`, `oauth2.googleapis.com`
- AI tùy chọn: `api.deepseek.com`

TLS được xác minh mặc định. Không cần API key để chạy demo/extractive. Việc có domain trong cấu hình không đồng nghĩa OAuth/API đã hoạt động.

## Mở rộng website

Module Gmail trả các trường `id`, `sender`, `subject`, `received_at`, `body`. Module website tương lai có thể trả cấu trúc tương tự rồi gọi `process(..., source="web")`; cần bổ sung link nguồn website trước khi dùng thực tế. Không cần OAuth nếu nguồn công khai.

## Tình trạng kiểm chứng

Đã chạy demo và kiểm thử tự động cho phân loại, MIME/HTML, chống xử lý trùng, chia ngày theo múi giờ, link Gmail và khả năng thử lại khi tóm tắt lỗi. Đã kiểm thử API quản trị và OAuth giả lập, lưu cấu hình/lịch chạy; đã thử trình duyệt thật cho đăng nhập, demo, tìm kiếm, tải file, thêm/xóa rules và lưu cài đặt trên desktop/mobile. Đã bổ sung kiểm thử AI JSON/cache/review, PDF có chữ, PDF scan vào review, Gmail PDF qua API giả lập, nâng cấp database và sửa nhóm. Chưa kiểm chứng OAuth với Google, Gmail thật, DeepSeek thật vì chưa có credentials. Không coi demo là bằng chứng kết nối tài khoản đã hoạt động.

### Cập nhật dễ hơn trên Linux (bản mã nguồn)

Mở bằng `Mo-So-Ghi-Chep.sh`, vào **Cài đặt → Cập nhật tool**. Bản thử này tải nhánh `codex/partner-linux-test`, kiểm tra gói tải về, chờ phiên cũ tắt, sao lưu mã rồi mở lại. Không thay `.local`, `.venv`, `.env` hoặc file đăng nhập. Mã cũ nằm trong `.local/updates/backup-*`. Nếu kiểm tra nhập module hoặc cài phụ thuộc thất bại, mã được phục hồi; thay đổi phụ thuộc đã cài vào `.venv` không được tự hoàn tác. Bản cập nhật không tự xóa các file cũ không còn trong nhánh.

Có thể chạy `Cap-Nhat-So-Ghi-Chep.sh` bằng **Run as a Program / Run in Terminal**. Nếu đang chạy bằng lệnh `python -m mailnotes.web`, nhấn Ctrl+C ở cửa sổ đó trước lần cập nhật đầu tiên. Không cập nhật khi tài liệu đang xử lý. Nếu cập nhật lỗi trước khi dừng app, app cũ tiếp tục chạy; xem thông báo trong Cài đặt hoặc `.local/admin/update.log`.

Để Chrome chỉ cần bấm **Reload** tại `chrome://extensions` sau mỗi lần cập nhật, nạp tiện ích một lần từ thư mục `chrome-extension` **bên trong thư mục tool đang dùng**, thay cho bản giải nén ở thư mục Downloads khác. Khi đổi thư mục tiện ích, có thể cần nhập lại địa chỉ tool và mã ghép nối. Bản đóng gói và macOS chưa dùng trình cập nhật này.
