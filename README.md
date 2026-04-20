📚 Manga Downloader (TopTruyenTV)

Script Python giúp tải truyện tranh từ trang TopTruyenTV và tự động chuyển thành file PDF. Hỗ trợ tải nhiều chapter, vượt Cloudflare (bằng cookie hoặc Selenium), và ghép ảnh thành PDF tiện đọc offline.

🚀 Tính năng
📋 Tự động lấy danh sách chapter từ URL truyện
📥 Tải toàn bộ ảnh của từng chapter
📄 Ghép ảnh thành file PDF
🔀 Hỗ trợ 2 chế độ:
1 PDF cho tất cả chapter
1 PDF riêng cho mỗi chapter
🍪 Hỗ trợ cookie cf_clearance để vượt Cloudflare
🤖 Tự động lấy cookie bằng Selenium (nếu cần)
🧠 Tự động lọc ảnh rác (quảng cáo, logo, banner)
🧰 Yêu cầu

Cài Python 3.8+

Cài các thư viện cần thiết:

pip install requests beautifulsoup4 pillow selenium

⚠️ Selenium cần cài thêm ChromeDriver phù hợp với phiên bản Chrome

📦 Cách sử dụng
1. Chạy chương trình
python main.py
2. Nhập thông tin
URL truyện (ví dụ):
https://www.toptruyentv11.com/truyen-tranh/ten-truyen
Cookie cf_clearance (có thể bỏ qua)
3. Chọn chapter

Nhập:

Chapter bắt đầu
Chapter kết thúc
4. Chọn chế độ PDF
1 → Gộp tất cả chapter thành 1 PDF
2 → Mỗi chapter 1 PDF riêng

🍪 Vượt Cloudflare
Cách 1: Dùng cookie thủ công
Mở web bằng Chrome
Nhấn F12 → Application → Cookies
Copy giá trị cf_clearance
Dán vào khi chương trình yêu cầu
Cách 2: Tự động (Selenium)
Script sẽ mở Chrome headless
Chờ ~30 giây để xác thực
Tự lấy cookie
⚠️ Lưu ý
Website có thể thay đổi cấu trúc HTML → cần chỉnh lại selector
Nếu bị lỗi 403 hoặc 503 → cần cookie mới
Tốc độ tải có delay để tránh bị block
Chỉ nên dùng cho mục đích học tập / cá nhân
🛠️ Công nghệ sử dụng
requests – gửi HTTP request
BeautifulSoup – parse HTML
Pillow – xử lý ảnh & tạo PDF
Selenium – bypass Cloudflare
