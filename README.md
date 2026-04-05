# FreeCell AI Solver

**FreeCell AI Solver** là một ứng dụng mô phỏng trò chơi bài FreeCell, tích hợp các thuật toán trí tuệ nhân tạo nhằm tự động tìm kiếm lời giải và cung cấp giao diện trực quan cho người dùng.

---

## 1. Thành viên thực hiện

- **Nguyễn Gia Khánh** - MSSV: 24127184  
- **Đào Duy Hoàng** - MSSV: 24127376  
- **Nguyễn Minh Phát** - MSSV: 24127489

---

## 2. Giới thiệu tổng quan

Dự án phát triển hệ thống mô phỏng game FreeCell với khả năng cho phép người dùng tự chơi (manual mode) hoặc tích hợp các thuật toán tìm kiếm (AI solver) để tự động tìm kiếm lời giải cho các ván bài từ mức độ Dễ đến Khó.

### Các tính năng chính
- **Tự động giải quyết:** Hỗ trợ giải tự động các cấp độ từ dễ đến khó (Easy / Hard).
- **Chế độ chơi thủ công:** Hỗ trợ kéo thả, hiệu ứng di chuyển bài mượt mà.
- **Bảng thống kê (Dashboard):** Giao diện trực quan đánh giá hiệu năng của từng chiến lược tìm kiếm.
- **Phân tích hiệu suất:** So sánh thời gian chạy, số node mở rộng và kích thước bộ nhớ qua biểu đồ.
- **Chi tiết từng test case:** Cho phép người dùng xem insight của từng hạt giống (seed) hoặc bài toán cụ thể.

### Thuật toán trí tuệ nhân tạo kết hợp

#### Uninformed Search (Tìm kiếm mù)
- **BFS (Breadth-First Search):** Đảm bảo tìm được lời giải có số bước đi ít nhất nếu tồn tại.
- **DFS (Depth-First Search):** Tìm kiếm theo chiều sâu, ưu tiên duyệt sâu vào các nhánh.

#### Informed Search (Tìm kiếm có thông tin)
- **UCS (Uniform Cost Search):** Tối ưu theo chi phí của từng bước đi.
- **A* (A-Star):** Sử dụng hàm Heuristic kết hợp với chi phí độ sâu để tối ưu tốc độ và độ phân nhánh (branching factor).

---

## 3. Cấu trúc thư mục dự án

```text
FreeCell-Solver/
├── backend/                # Hệ thống Logic backend chuyên sâu và API (Python Flask)
│   ├── solvers/            # Triển khai các thuật toán AI (BFS, DFS, UCS, A*)
│   ├── tests/              # Danh sách các tệp chứa test case cấu hình bài
│   ├── app.py              # Tệp chạy chính (Entry point), thiết lập Server & SocketIO
│   ├── game_state.py       # Quản lý trạng thái, nước đi, logic ràng buộc của dự án FreeCell
│   └── requirements.txt    # Khai báo các thư viện Python
├── frontend/               # Giao diện Web Client tương tác trực quan (React, Vite)
│   ├── public/             # Dữ liệu hình ảnh và tài nguyên tĩnh
│   ├── src/                # Mã nguồn chính dự án frontend
│   │   ├── components/     # Nhóm các thành phần UI độc lập
│   │   ├── layouts/        # Component thiết kế khung bố trí chuẩn
│   │   ├── pages/          # Các màn hình chính (Home, Statistics Analytics)
│   │   ├── redux/          # Kiến trúc State trung tâm (Redux Toolkit)
│   │   ├── hooks/          # Custom Hooks dùng lại logic
│   │   ├── App.jsx         # Lời gọi Root Routing
│   │   └── main.jsx        # Đầu nối ứng dụng vào DOM
│   ├── package.json        # Cấu trúc npm dependency
│   └── vite.config.js      # Công cụ xây dựng và biên dịch cho Vite
└── package-lock.json

```

## 4. Công nghệ sử dụng

### Backend
- **Ngôn ngữ:** Python 3.9+
- **Framework:** Flask
- **Hỗ trợ:** Flask-SocketIO (Real-time events), Flask-CORS

### Frontend
- **Framework:** React (Vite)
- **Styling:** Tailwind CSS
- **State Management:** Redux Toolkit
- **Data Visualization:** Recharts
- **Giao tiếp API:** Axios, Socket.IO Client

---

## 5. Hướng dẫn cài đặt và chạy chương trình

Dự án bao gồm hai phần: Backend và Frontend. Thực hiện các bước sau để khởi chạy cục bộ:

### Bước 1: Khởi chạy Backend (Flask)

1. Mở terminal và di chuyển vào thư mục `backend/`:
   ```bash
   cd backend
   ```
2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```
3. Khởi chạy server:
   ```bash
   python app.py
   ```
   > Server Python sẽ khởi động tại địa chỉ: `http://localhost:5000`

### Bước 2: Khởi chạy Frontend (React + Vite)

1. Mở một terminal mới và di chuyển vào thư mục `frontend/`:
   ```bash
   cd frontend
   ```
2. Cài đặt các thẻ viện NPM:
   ```bash
   npm install
   ```
3. Khởi động môi trường dev:
   ```bash
   npm run dev
   ```

**Giao diện trò chơi sẽ mặc định được phục vụ tại:** [http://localhost:5173](http://localhost:5173)

---
