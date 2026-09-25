# ⚡ Auto-Vote Real Web Pro (Level 1, Proxy Pool, CSRF & Cookie Bypass)

Công cụ tự động hóa bình chọn chuyên nghiệp dành cho các trang web bình chọn thật (**Real-World Voting Websites**) và hệ thống chống bình chọn Cấp độ 1 (Level 1).

---

## 🧐 Tại sao các Tool thông thường không chạy được trên "Web thật"?
Trang web bình chọn thật trên Internet có nhiều cơ chế bảo vệ phức tạp hơn web thử nghiệm local:
1. **Kiểm tra HTTP Origin & Referer**: Nhiều trang web chặn request nếu không gửi từ đúng Domain gốc của trang web.
2. **Chặn IP (IP Rate Limit / Cloudflare)**: Gửi nhiều lượt vote từ cùng 1 IP nhà mạng sẽ bị WAF/Server khóa IP. Header giả `X-Forwarded-For` bị server loại bỏ.
3. **Mã Bảo Mật CSRF Token / Nonce**: Mỗi lượt vote yêu cầu một mã Token ngẫu nhiên được cấp khi tải trang HTML.
4. **Định dạng Form (`application/x-www-form-urlencoded`)**: Các trang web thật thường dùng `<form>` truyền thống thay vì JSON.
5. **Đồng bộ Header Trình duyệt (Sec-CH-UA, User-Agent)**: Giả lập đầy đủ thông số trình duyệt Chrome/Firefox/Edge thực tế.

---

## 🚀 Các Tính Năng Đột Phá Mới Dành Cho "Web Thật"

### 1️⃣ **Smart Target Web Analyzer (Dò Web Tự Động)**
- Chỉ cần nhập URL trang web bình chọn thật (ví dụ `https://web-binh-chon.com/poll/123`).
- Hệ thống tự động tải HTML, phân tích các thẻ `<form>`, tìm **API Endpoint nhận vote**, **Radio Button tùy chọn**, và **Mã CSRF Token**.
- Tự động điền cấu hình vào Tool chỉ với **1 cú click**!

### 2️⃣ **Proxy Rotation Pool (Xoay Vòng Proxy)**
- Hỗ trợ danh sách Proxy (HTTP, HTTPS, SOCKS4, SOCKS5).
- Tự động xoay vòng Proxy cho từng luồng/lượt vote, vượt qua hoàn toàn cơ chế chặn IP rate limit của web thật.

### 3️⃣ **Tự Động Lấy CSRF Token / Nonce Trước Mỗi Lượt Vote**
- Bật tính năng **Auto-Fetch CSRF**: Tool sẽ tự động GET trang web trước, trích xuất mã `csrf_token`, `_token` hoặc `nonce` từ `<input>` / `<meta>` tag, sau đó đính kèm vào lượt POST vote.

### 4️⃣ **Tự Động Tạo Header Origin / Referer Đội Lốt Trình Duyệt Thực**
- Tự động trích xuất Origin (`https://domain.com`) và Referer từ Target URL.
- Đồng bộ `User-Agent` với bộ header `sec-ch-ua`, `sec-ch-ua-platform`, `sec-fetch-*`.

### 5️⃣ **Script Console F12 Chạy Trực Tiếp Trên Trình Duyệt**
- Tạo sẵn đoạn mã JS tự động đọc DOM của trang web thật, vượt qua rào cản CORS và tự động xóa Cookie / LocalStorage / SessionStorage ngay trong DevTools F12 của Chrome/Firefox.

---

## 🛠 Cấu trúc Repository

```
Tool-Vote1-main/
├── app.py                  # Flask Controller Dashboard (Web GUI)
├── voter_engine.py         # Engine Async Voting (Proxy Pool, CSRF & Header Rotation)
├── cli.py                  # CLI High-Speed Command Line Tool
├── sample_test_server.py   # Web bình chọn mẫu Level 1 để TEST local
├── templates/
│   └── index.html          # Giao diện Web GUI Cyberpunk Glassmorphism
├── static/
│   ├── css/style.css       # Style Dark Mode Neon
│   └── js/app.js           # Frontend Logic, Tab Switcher & Real Web Analyzer
├── browser_scripts/
│   └── console_voter.js    # Script JS chạy trực tiếp trong F12 Console của trang web thật
└── requirements.txt        # Thư viện Python yêu cầu
```

---

## 📖 Hướng Dẫn Sử Dụng Chi Tiết

### 1️⃣ Chạy Giao Diện Web GUI (Khuyên Dùng)

Kích hoạt môi trường và chạy Web Dashboard:
```bash
python app.py
```
- Mở trình duyệt truy cập: **`http://127.0.0.1:5000`**

#### Các bước thao tác trên Web GUI:
1. Sang tab **"Dò Web Tự Động"** -> Nhập URL trang web bình chọn thật -> Nhấn **Phân Tích & Tự Động Điền Cấu Hình**.
2. Sang tab **"Proxies & IP"** -> Dán danh sách Proxy (nếu trang web chặn IP).
3. Sang tab **"CSRF & Token"** -> Bật tự động lấy CSRF token nếu trang web yêu cầu mã token bảo mật.
4. Nhấn **"Test 1 Vote"** để kiểm tra phản hồi từ Server.
5. Nhấn **"Start Auto Vote"** để bắt đầu chiến dịch bình chọn hàng loạt!

---

### 2️⃣ Sử Dụng CLI Tool (Dòng Lệnh Siêu Tốc)

Chạy trực tiếp từ Terminal với Proxy & CSRF Auto-Fetch:
```bash
python cli.py --url https://web-binh-chon.com/api/vote --method POST --payload "{\"option_id\":\"1\"}" --payload-type form --threads 10 --proxies proxies.txt --fetch-csrf --csrf-page-url https://web-binh-chon.com/poll/123
```

- `--url`: API Endpoint nhận vote.
- `--payload-type`: `json` hoặc `form` (x-www-form-urlencoded).
- `--proxies`: File chứa danh sách proxy (1 proxy / dòng) hoặc chuỗi phân cách bởi dấu phẩy.
- `--fetch-csrf`: Tự động lấy CSRF Token từ trang web trước khi vote.
- `--insecure`: Tắt xác thực SSL nếu web bị lỗi chứng chỉ.

---

### 3️⃣ Chạy Trực Tiếp Trong F12 Console Trình Duyệt

Nếu bạn đang mở sẵn trang web bình chọn thật trên Google Chrome / Firefox:
1. Nhấn `F12` trên bàn phím -> Chọn tab **Console**.
2. Mở file [browser_scripts/console_voter.js](file:///c:/Users/admin/Downloads/Tool-Vote1-main/Tool-Vote1-main/browser_scripts/console_voter.js) (hoặc bấm nút **Copy Script JS** trên Web GUI).
3. Dán vào Console và nhấn `Enter`.
4. Script sẽ tự động xóa Cookie / LocalStorage, tự tìm CSRF token trên DOM và gửi lượt vote liên tục với bảng điều khiển HUD trực tiếp trên góc màn hình!

---

## 🛡️ Mẹo Xử Lý Sự Cố Với Web Thật
- **Lỗi HTTP 403 Forbidden / 400 Bad Request**: Web yêu cầu `Referer` hoặc `CSRF Token`. Sử dụng tab **Dò Web Tự Động** để tự động bổ sung.
- **Lỗi bị khóa IP sau vài lượt vote**: Thêm danh sách Proxy vào tab **Proxies & IP**.
- **Web dùng Form truyền thống**: Chọn định dạng Payload là `Form Data (url-encoded)`.
