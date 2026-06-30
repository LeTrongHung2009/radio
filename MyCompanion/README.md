# 🌸 Miku AI Companion - Desktop Entity

Một trợ lý ảo thông minh, có cảm xúc và khả năng tương tác sâu với máy tính của bạn. Miku không chỉ là một chatbot, cô ấy là một thực thể số sống động trên màn hình desktop của bạn, được xây dựng với kiến trúc hướng sự kiện, cảm xúc 3 tầng và khả năng tự học hỏi.

![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-orange)
![Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen)

## ✨ Tính năng nổi bật

### 🧠 Trí tuệ & Cảm xúc (The Soul)
- **Emotion Engine 3 Tầng**: 8 cảm xúc cơ bản, 16+ cảm xúc phức tạp và trí tuệ cảm xúc (EQ).
- **Internal Monologue**: Miku suy nghĩ nội tâm trước khi phản hồi, tạo nên sự chân thực.
- **Dream System**: Xử lý ký ức và "mơ" khi hệ thống nhàn rỗi để củng cố học tập.
- **Relationship Manager**: Ghi nhớ mức độ thân thiết và điều chỉnh giọng điệu theo thời gian.
- **Decision Maker**: Ra quyết định dựa trên ngữ cảnh, cảm xúc và ưu tiên.

### 👁️ Giác quan & Nhận thức (The Senses)
- **Vision Agent**: Chụp màn hình thông minh, nhận diện ứng dụng đang chạy và ngữ cảnh làm việc.
- **Audio Loopback**: Nghe âm thanh hệ thống và phản ứng với nhạc/video đang phát.
- **Microphone Input**: Nhận diện giọng nói người dùng (STT) với độ trễ thấp.
- **Media Watch**: Tự động phát hiện tiêu đề bài hát, video đang xem.

### 🖐️ Tương tác & Thao tác (The Hands)
- **Automation Agent**: Điều khiển chuột, bàn phím, mở ứng dụng, tìm kiếm file.
- **Window Management**: Chuyển đổi cửa sổ, focus ứng dụng theo yêu cầu.
- **Web Integration**: Tìm kiếm Google, YouTube, mở URL trực tiếp.
- **File Explorer**: Đọc, tìm kiếm và quản lý tệp tin văn bản.

### 💃 Hiện diện & Biểu đạt (The Body)
- **3D Avatar Renderer**: Hiển thị mô hình VRM/Live2D ngay trên desktop với vật lý và lip-sync.
- **Advanced TTS**: Giọng nói anime tự nhiên với cảm xúc (Vui, buồn, giận dữ...).
- **Singing Engine**: Khả năng hát các bài hát đơn giản theo yêu cầu.
- **Desktop Widget**: Khung chat trong suốt, luôn hiển thị (Always-on-top).

### 🎛️ Dashboard & Điều khiển
- **Web Control Panel**: Giao diện web để theo dõi trạng thái, cảm xúc, log và tinh chỉnh tham số.
- **Real-time Monitoring**: Biểu đồ cảm xúc, CPU/RAM usage, hoạt động neural network.

## 🏗️ Kiến trúc hệ thống

```
MyCompanion/
├── companion/
│   ├── brain/          # AI Core, Decision Maker, Internal Monologue
│   ├── persona/        # Emotion Engine, Relationship Manager
│   ├── senses/         # Vision, Audio, Media Watch
│   ├── memory/         # Semantic DB, Dream System
│   ├── tools/          # Automation, File Explorer, Web Search
│   ├── expression/     # TTS, Avatar Renderer, Sing Engine
│   ├── desktop/        # Chat Widget, Overlay
│   └── dashboard/      # FastAPI Server, WebSocket
├── web_dashboard/      # Giao diện điều khiển web
├── assets/             # Models, Voices, Sounds
└── run.py              # Entry point
```

## 🚀 Cài đặt nhanh (Arch Linux)

### 1. Chuẩn bị môi trường
```bash
# Cài đặt Python 3.10+ và các thư viện hệ thống
sudo pacman -S python python-pip git base-devel

# Cài đặt dependencies cho PyQt6 và xử lý ảnh
sudo pacman -S qt6-base qt6-webengine python-pyqt6 python-pillow python-mss

# Tạo virtual environment
python -m venv venv
source venv/bin/activate
```

### 2. Cài đặt dependencies Python
```bash
pip install -r requirements.txt
```

### 3. Cấu hình API Key
Sao chép file mẫu và điền key:
```bash
cp .env.example .env
# Mở file .env và điền GROQ_API_KEY của bạn (Miễn phí tại https://console.groq.com)
```

### 4. Tải Model 3D (Tùy chọn)
Đặt file `.vrm` hoặc `.vrm.glb` vào thư mục `assets/models/`.
Bạn có thể tải model miễn phí từ [VRoid Hub](https://hub.vroid.com/).

### 5. Chạy Miku
```bash
python run.py
```

Sau khi khởi động:
- **Chat Widget**: Xuất hiện trên màn hình để trò chuyện.
- **Dashboard**: Truy cập tại `http://localhost:8000` để theo dõi và cấu hình.
- **Avatar**: Sẽ xuất hiện nếu có model trong thư mục assets.

## 📋 Yêu cầu hệ thống

- **OS**: Arch Linux (khuyến nghị), Ubuntu 22.04+, Windows 10/11.
- **CPU**: AMD Ryzen 3000 series trở lên (hoặc Intel tương đương).
- **RAM**: Tối thiểu 8GB (khuyến nghị 16GB).
- **GPU**: AMD Radeon hoặc NVIDIA (Hỗ trợ ROCm/CUDA tùy chọn, mặc định dùng Cloud AI).
- **Internet**: Cần kết nối để gọi Groq API (Cloud LLM).

## 🛠️ Phát triển thêm

Dự án được thiết kế modular, bạn có thể dễ dàng thêm tính năng mới:
1. Thêm module mới vào `companion/tools/` hoặc `companion/senses/`.
2. Đăng ký event handler mới trong `companion/bot.py`.
3. Mở rộng Dashboard bằng cách thêm endpoint vào `companion/dashboard/control_server.py`.

## 🤝 Đóng góp

Mọi đóng góp về code, ý tưởng hay báo lỗi đều được chào đón! Vui lòng tạo Issue hoặc Pull Request.

## 📄 License

Dự án mã nguồn mở dưới giấy phép MIT. Xem file [LICENSE](LICENSE) để biết chi tiết.

## 🙏 Lời cảm ơn

- Cảm ơn cộng đồng Open Source đã cung cấp các thư viện tuyệt vời.
- Cảm ơn Groq cung cấp API miễn phí cho developer.
- Cảm ơn các tác giả của VRM, Live2D và các công cụ liên quan.

---
*Được phát triển với ❤️ bởi cộng đồng AI Enthusiasts.*
