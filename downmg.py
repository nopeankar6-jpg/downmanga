import requests
from bs4 import BeautifulSoup
import os
from typing import List, Dict
import time
import re

try:
    from PIL import Image as PILImage

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


class MangaDownloader:
    def __init__(self, manga_url: str, cf_clearance_cookie: str = None):
        """
        manga_url: URL trang chính của truyện (không phải URL chapter)
                   Ví dụ: https://www.toptruyentv11.com/truyen-tranh/do-de-cua-ta-deu-la-dai-phan-phai
        """
        self.manga_url = manga_url
        self.session = requests.Session()
        self.output_dir = "manga_download"
        os.makedirs(self.output_dir, exist_ok=True)
        self.chapter_urls = {}  # Dict {chapter_number: full_url}

        # Setup headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.toptruyenssi.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })

        # Thêm cookie nếu có
        if cf_clearance_cookie:
            # Thêm cookie cho nhiều domain khác nhau
            domains = ['anhvip.xyz', 'toptruyentv11.com', 'topcdnv1.art', 'imgvip.xyz']
            for domain in domains:
                self.session.cookies.set('cf_clearance', cf_clearance_cookie, domain=domain)
            print("✓ Đã thêm cookie cf_clearance cho các domain")
        else:
            print("⚠️ Không có cookie. Script sẽ cố gắng tải...")

    def get_cookie_selenium(self, url: str) -> str:
        """Lấy cookie tự động bằng Selenium"""
        if not HAS_SELENIUM:
            print("❌ Selenium chưa cài. Cài: pip install selenium")
            return None

        try:
            print("🌐 Mở trình duyệt để lấy cookie...")
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            print("⏳ Chờ Cloudflare xác thực (30 giây)...")
            time.sleep(30)

            cookies = driver.get_cookies()
            cf_cookie = None
            for cookie in cookies:
                if cookie['name'] == 'cf_clearance':
                    cf_cookie = cookie['value']
                    # Thêm cookie cho nhiều domain
                    domains = ['anhvip.xyz', 'toptruyentv11.com', 'topcdnv1.art', 'imgvip.xyz']
                    for domain in domains:
                        self.session.cookies.set('cf_clearance', cf_cookie, domain=domain)
                    break

            driver.quit()

            if cf_cookie:
                print(f"✅ Lấy cookie thành công: {cf_cookie[:50]}...")
                return cf_cookie
            else:
                print("⚠️ Không tìm thấy cookie cf_clearance")
                return None

        except Exception as e:
            print(f"❌ Lỗi lấy cookie: {e}")
            return None

    def fetch_chapter_list(self) -> Dict[int, str]:
        """
        Lấy danh sách tất cả các chapter từ trang chính của truyện
        Returns: Dict {chapter_number: full_chapter_url}
        """
        print(f"📋 Đang lấy danh sách chapter từ: {self.manga_url}")
        try:
            response = self.session.get(self.manga_url, timeout=15)

            if response.status_code != 200:
                print(f"❌ Không thể tải trang chính (Status: {response.status_code})")
                if response.status_code in [503, 403]:
                    print("⚠️ Có thể bị chặn bởi Cloudflare. Thử lấy cookie mới...")
                    if self.get_cookie_selenium(self.manga_url):
                        response = self.session.get(self.manga_url, timeout=15)
                        if response.status_code != 200:
                            return {}
                    else:
                        return {}
                else:
                    return {}

            soup = BeautifulSoup(response.text, 'html.parser')
            chapter_dict = {}

            # Tìm các thẻ chứa danh sách chapter
            # Thử nhiều selector phổ biến
            selectors = [
                ('div', {'class': re.compile(r'chapter|list-chapter|chapter-list')}),
                ('ul', {'class': re.compile(r'chapter|list-chapter')}),
                ('div', {'id': re.compile(r'chapter|list-chapter')}),
            ]

            chapter_container = None
            for tag, attrs in selectors:
                chapter_container = soup.find(tag, attrs)
                if chapter_container:
                    break

            # Nếu không tìm thấy container, tìm toàn bộ trang
            if not chapter_container:
                chapter_container = soup

            # Tìm tất cả link chapter với pattern /chapter-số/ID
            chapter_links = chapter_container.find_all('a', href=re.compile(r'/chapter-\d+/\d+'))

            # Nếu vẫn không có, thử tìm bất kỳ link nào có chữ "chapter"
            if not chapter_links:
                chapter_links = chapter_container.find_all('a', href=re.compile(r'chapter-\d+'))

            print(f"   🔍 Tìm thấy {len(chapter_links)} link chapter trong HTML")

            for link in chapter_links:
                href = link.get('href')
                if not href:
                    continue

                # Đảm bảo URL đầy đủ
                if href.startswith('/'):
                    full_url = 'https://www.toptruyentv11.com' + href
                elif not href.startswith('http'):
                    full_url = 'https://www.toptruyentv11.com/' + href
                else:
                    full_url = href

                # Trích xuất số chapter từ URL
                match = re.search(r'/chapter-(\d+)/', full_url)
                if match:
                    chapter_num = int(match.group(1))
                    # Chỉ lưu nếu chưa có hoặc để tránh trùng lặp
                    if chapter_num not in chapter_dict:
                        chapter_dict[chapter_num] = full_url

            if chapter_dict:
                print(f"✅ Tìm thấy {len(chapter_dict)} chapter")
                # Hiển thị vài chapter đầu và cuối
                sorted_chapters = sorted(chapter_dict.keys())
                display_start = sorted_chapters[:3]
                display_end = sorted_chapters[-3:] if len(sorted_chapters) > 6 else []

                for ch in display_start:
                    print(f"   Chapter {ch}: {chapter_dict[ch]}")
                if display_end and display_end[0] not in display_start:
                    print(f"   ...")
                    for ch in display_end:
                        print(f"   Chapter {ch}: {chapter_dict[ch]}")
            else:
                print("❌ Không tìm thấy chapter nào")
                print("   💡 Gợi ý: Kiểm tra HTML của trang để tìm đúng selector")

            return chapter_dict

        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách chapter: {e}")
            import traceback
            print(f"   Chi tiết: {traceback.format_exc()}")
            return {}

    def download_page(self, chapter_url: str, chapter_num: int) -> str:
        """Tải HTML từ URL chapter"""
        try:
            print(f"📥 Đang tải chapter {chapter_num}...")
            print(f"   URL: {chapter_url}")
            response = self.session.get(chapter_url, timeout=10)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                print(f"   ✓ Tải thành công ({len(response.text)} ký tự)")
                return response.text
            else:
                print(f"   ❌ Status code: {response.status_code}")
                if response.status_code in [503, 403] and self.get_cookie_selenium(chapter_url):
                    print("🔄 Thử tải lại sau khi lấy cookie mới...")
                    response = self.session.get(chapter_url, timeout=10)
                    if response.status_code == 200:
                        print(f"   ✓ Tải lại thành công ({len(response.text)} ký tự)")
                        return response.text
                return ""
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
            return ""

    def extract_images(self, html: str) -> List[str]:
        """Trích xuất URL ảnh từ HTML"""
        try:
            print("   🔍 Phân tích HTML...")
            soup = BeautifulSoup(html, 'html.parser')

            chapter_content = soup.find('div', class_='chapter-content')
            if not chapter_content:
                chapter_content = soup

            img_urls = []
            all_imgs = chapter_content.find_all('img')

            # Danh sách các domain ảnh phổ biến của toptruyentv11
            valid_domains = ['anhvip', 'topcdnv1', 'topcdn', 'imgvip', 'imageserver']

            for img in all_imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if not src:
                    continue

                # Sửa URL thiếu scheme (//domain.com -> https://domain.com)
                if src.startswith('//'):
                    src = 'https:' + src
                elif not src.startswith('http'):
                    # Nếu là relative URL
                    src = 'https://www.toptruyentv11.com' + (src if src.startswith('/') else '/' + src)

                # Kiểm tra extension
                if not any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    continue

                # Lọc quảng cáo - bỏ qua ảnh logo/banner
                if any(ad in src.lower() for ad in
                       ['ads', 'banner', 'logo', 'icon', 'avatar', 'quang-cao', '/top/toptv']):
                    continue

                # Chỉ lấy ảnh từ các domain ảnh hợp lệ
                # Kiểm tra xem URL có chứa bất kỳ domain nào trong danh sách
                is_valid = False
                for domain in valid_domains:
                    if domain in src.lower():
                        is_valid = True
                        break

                # Thêm điều kiện: phải có 'image' hoặc 'img' trong path (tránh ảnh rác)
                if is_valid and any(
                        keyword in src.lower() for keyword in ['image_comics', 'image_top', '/img_', 'images/']):
                    img_urls.append(src)

            # Loại bỏ trùng lặp
            img_urls = list(dict.fromkeys(img_urls))

            # Sắp xếp theo số thứ tự trong tên file
            try:
                def extract_img_number(url):
                    # Tìm pattern img_XXX hoặc imgXXX
                    match = re.search(r'img[_-]?(\d+)', url.lower())
                    if match:
                        return int(match.group(1))
                    return 0

                img_urls.sort(key=extract_img_number)
            except Exception as e:
                print(f"   ⚠️ Không thể sắp xếp ảnh: {e}")

            print(f"   ✅ Tìm thấy {len(img_urls)} ảnh")

            # Debug: Hiển thị vài URL đầu tiên để kiểm tra
            if img_urls:
                print(f"   📸 Ảnh đầu: {img_urls[0][:80]}...")
                if len(img_urls) > 1:
                    print(f"   📸 Ảnh cuối: {img_urls[-1][:80]}...")

            return img_urls

        except Exception as e:
            print(f"   ❌ Lỗi phân tích: {e}")
            import traceback
            print(f"   Chi tiết: {traceback.format_exc()}")
            return []

    def download_images(self, image_urls: List[str], chapter: int) -> List[str]:
        """Tải tất cả ảnh"""
        saved_images = []
        total = len(image_urls)

        for idx, url in enumerate(image_urls, 1):
            try:
                self.session.headers.update({'Referer': self.manga_url})
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    chapter_dir = os.path.join(self.output_dir, f"chapter_{chapter:02d}")
                    os.makedirs(chapter_dir, exist_ok=True)

                    filename = os.path.join(chapter_dir, f"ch{chapter:02d}_img_{idx:03d}.jpg")
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    saved_images.append(filename)
                    print(f"   ✓ Ảnh {idx}/{total}")
                else:
                    print(f"   ❌ Status code tải ảnh {idx}: {response.status_code}")
                time.sleep(0.2)
            except Exception as e:
                print(f"   ❌ Lỗi tải ảnh {idx}: {e}")
                continue

        print(f"   ✅ Tải {len(saved_images)}/{total} ảnh thành công\n")
        return saved_images

    def create_pdf(self, image_files: List[str], output_pdf: str):
        """Ghép ảnh thành PDF"""
        if not HAS_PILLOW:
            print("⚠️ Pillow chưa cài. Cài: pip install pillow")
            return False

        try:
            if not image_files:
                print("❌ Không có ảnh")
                return False

            print("   📄 Ghép ảnh thành PDF...")

            sorted_files = sorted(image_files)
            images = []

            for img_path in sorted_files:
                try:
                    img = PILImage.open(img_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    print(f"   ⚠️ Lỗi mở ảnh: {img_path} - {e}")
                    continue

            if images:
                pdf_path = os.path.join(self.output_dir, output_pdf)
                images[0].save(pdf_path, save_all=True, append_images=images[1:])
                print(f"   ✅ PDF tạo thành công: {pdf_path}\n")
                return True
            else:
                print("❌ Không còn ảnh hợp lệ để tạo PDF.")
                return False

        except Exception as e:
            print(f"   ❌ Lỗi tạo PDF: {e}\n")
            return False

    def run(self):
        """Chạy toàn bộ"""
        print("=" * 60)
        print("🎬 MANGA DOWNLOADER")
        print("=" * 60)

        # Bước 1: Lấy danh sách chapter
        self.chapter_urls = self.fetch_chapter_list()

        if not self.chapter_urls:
            print("\n❌ Không lấy được danh sách chapter. Kiểm tra lại URL hoặc thử lấy cookie mới.")
            print("\n❓ Bạn có muốn lấy cookie mới tự động? (Cần Selenium + Chrome)")
            choice = input("Chọn Y/N (default N): ").strip().upper()
            if choice == 'Y':
                if HAS_SELENIUM:
                    self.get_cookie_selenium(self.manga_url)
                    self.chapter_urls = self.fetch_chapter_list()
                    if not self.chapter_urls:
                        print("❌ Vẫn không lấy được danh sách chapter. Thoát.")
                        return
                else:
                    print("❌ Selenium chưa cài.")
                    return
            else:
                return

        available_chapters = sorted(self.chapter_urls.keys())
        print(f"\n📚 Có {len(available_chapters)} chapter: {available_chapters[0]} - {available_chapters[-1]}")

        try:
            start_ch = int(input("\n📖 Chapter bắt đầu: "))
            end_ch = int(input("📖 Chapter kết thúc: "))
        except ValueError:
            print("❌ Nhập số hợp lệ")
            return

        # Kiểm tra chapter có tồn tại không
        chapters_to_download = [ch for ch in range(start_ch, end_ch + 1) if ch in self.chapter_urls]

        if not chapters_to_download:
            print(f"❌ Không tìm thấy chapter nào trong khoảng {start_ch}-{end_ch}")
            return

        print(f"\n✅ Sẽ tải {len(chapters_to_download)} chapter: {chapters_to_download}")

        print("\n📋 CHỌN CHẾ ĐỘ:")
        print("1️⃣ Ghép nối (1 file PDF tất cả chapter)")
        print("2️⃣ Ghép đơn (1 file PDF cho mỗi chapter)")

        try:
            mode = int(input("\nChọn (1/2): "))
        except ValueError:
            print("❌ Nhập 1 hoặc 2")
            return

        all_images = {}

        for chapter in chapters_to_download:
            print(f"\n{'=' * 60}")
            print(f"Chapter {chapter}")
            print(f"{'=' * 60}")

            chapter_url = self.chapter_urls[chapter]
            html = self.download_page(chapter_url, chapter)
            if not html:
                continue

            image_urls = self.extract_images(html)
            if not image_urls:
                continue

            image_files = self.download_images(image_urls, chapter)
            if image_files:
                all_images[chapter] = image_files

            time.sleep(0.5)

        if not all_images:
            print("❌ Không tải được ảnh nào")
            return

        print(f"\n{'=' * 60}")
        print(f"TẠO PDF")
        print(f"{'=' * 60}\n")

        if mode == 1:
            merged_images = []
            for ch in sorted(all_images.keys()):
                merged_images.extend(all_images[ch])
            pdf_name = f"manga_ch_{start_ch:02d}_to_{end_ch:02d}.pdf"
            self.create_pdf(merged_images, pdf_name)
        elif mode == 2:
            for chapter, images in all_images.items():
                pdf_name = f"chapter_{chapter:02d}.pdf"
                self.create_pdf(images, pdf_name)
        else:
            print("⚠️ Chế độ không hợp lệ, không tạo PDF")

        print("=" * 60)
        print("✨ Hoàn thành!")
        print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("🎬 MANGA DOWNLOADER - TOPTRUYENTV11")
    print("=" * 60)

    # Nhập URL truyện
    print("\n📝 Nhập URL trang truyện (ví dụ: https://www.toptruyentv11.com/truyen-tranh/ten-truyen/12373)")
    manga_url = input("URL: ").strip()

    # Kiểm tra URL hợp lệ
    if not manga_url:
        print("❌ URL không được để trống!")
        exit()

    if not manga_url.startswith('http'):
        print("❌ URL không hợp lệ! Phải bắt đầu bằng http:// hoặc https://")
        exit()

    if 'toptruyentv' not in manga_url:
        print("⚠️ Cảnh báo: URL không phải từ toptruyentv11.com, có thể không hoạt động!")
        choice = input("Tiếp tục? (Y/N): ").strip().upper()
        if choice != 'Y':
            exit()

    # Hỏi về cookie
    print("\n🍪 Bạn có cookie cf_clearance không? (Để trống nếu không có)")
    print("   (Cookie giúp vượt qua Cloudflare protection)")
    CF_CLEARANCE_COOKIE = input("Cookie (Enter để bỏ qua): ").strip()

    if not CF_CLEARANCE_COOKIE:
        CF_CLEARANCE_COOKIE = None
        print("⚠️ Không có cookie - sẽ thử tải trực tiếp")

    print("\n" + "=" * 60)
    downloader = MangaDownloader(manga_url, CF_CLEARANCE_COOKIE)
    downloader.run()