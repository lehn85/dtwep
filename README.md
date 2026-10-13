# Digital Twin Energy Platform (DTEP)

Nền tảng Digital Twin cho mô phỏng đồng thời (co-simulation), hiệu chuẩn tự động (Genetic Algorithm calibration) và theo dõi suy thoái vật lý cho công trình năng lượng & nhà kính nông điện (Agrivoltaic Greenhouse).

Hệ thống được thiết kế theo kiến trúc **Multi-Case Platform** có khả năng tự động khám phá các use case trong thư mục `cases/` (ví dụ `greenhouse` và các case mở rộng trong tương lai).

---

## 🌟 Tính năng chính

- **Multi-Case Auto-Discovery**: Tự động phát hiện và quản lý danh sách use case từ thư mục `cases/`, hỗ trợ cấu hình siêu dữ liệu (`case.yaml`) và các thí nghiệm đi kèm.
- **Modern React + Vite Frontend**: Giao diện người dùng Dark Glassmorphic hiện đại, chuẩn UI/UX cao cấp, xây dựng với React 18, TypeScript, Tailwind CSS, Lucide Icons và Recharts.
- **Dual Config Editor**: Bộ chỉnh sửa cấu hình trực quan 2 chế độ:
  - *Visual Form Mode*: Thanh trượt (sliders) và ô nhập liệu cho tham số vật lý, bộ tối ưu GA, và trọng số hàm mất mát.
  - *YAML Editor Mode*: Trình soạn thảo mã YAML với kiểm tra cú pháp thời gian thực và lưu cấu hình tức thì.
- **Real-Time Execution Terminal**: Truyền phát log `stdout`/`stderr` và tiến độ thế hệ GA thời gian thực qua WebSocket (`/ws/run`).
- **Interactive Analytics & ASHRAE Compliance**:
  - Biểu đồ hội tụ GA (Convergence Curve) và biểu đồ chuỗi thời gian (Co-Sim Time-Series: Temp, PV, Battery SoC, Net Grid).
  - Bảng đối sánh và đánh giá chuẩn ASHRAE Guideline 14 (NMBE $\le \pm 10\%$, CVRMSE $\le 30\%$, $R^2 \ge 0.70$).
  - Thư viện ảnh đồ thị chất lượng cao (Plot Gallery với tính năng phóng to Lightbox & tải ảnh).

---

## 🏗️ Cấu trúc dự án

```
dtep/
├── app/
│   ├── case_manager.py          # Dịch vụ tự động quét và quản lý Cases & Configs & Results
│   ├── experiment_runner.py     # Quản lý tiến trình chạy thí nghiệm và stream WebSocket
│   └── ...
├── calibration_framework/       # Thư viện lõi framework hiệu chuẩn và tối ưu hóa (GA, Runner, Metrics)
├── cases/                       # Thư mục chứa các use case (Greenhouse, Office, v.v.)
│   └── greenhouse/
│       ├── case.yaml            # Siêu dữ liệu & mô tả case
│       ├── configs/             # Các tệp YAML cấu hình (exp1, exp2, exp3, calibration)
│       ├── exp1_accuracy.py     # Thí nghiệm 1: Độ chính xác & Tốc độ hội tụ
│       ├── exp2_scenarios.py    # Thí nghiệm 2: Đa kịch bản thời tiết & vận hành
│       ├── exp3_degradation.py  # Thí nghiệm 3: Theo dõi suy thoái & tái hiệu chuẩn
│       └── ...
├── data/                        # Tệp mô hình EnergyPlus (OSM, IDF) và dữ liệu thời tiết (EPW)
├── frontend/                    # Ứng dụng Web hiện đại (React 18 + Vite + TypeScript + Tailwind)
│   ├── src/                     # Mã nguồn Components, Services, Types
│   ├── dist/                    # Bản build production được FastAPI phục vụ
│   └── package.json
├── main.py                      # Server FastAPI (REST APIs, WebSocket, phục vụ SPA)
├── pyproject.toml               # Cấu hình dự án Python & dependencies
└── results/                     # Thư mục lưu kết quả thí nghiệm, metrics.csv và đồ thị plots/
```

---

## 🚀 Cài đặt và Chạy

### 1. Yêu cầu hệ thống
- Python $\ge 3.12$
- [uv](https://docs.astral.sh/uv/) (Package manager cho Python)
- Node.js $\ge 18$ & npm

### 2. Cài đặt Python dependencies
```bash
uv sync
```

### 3. Cài đặt và Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Khởi chạy Server
Khởi động FastAPI server:
```bash
uv run python main.py
```
Hoặc chạy với Uvicorn:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **Truy cập Giao diện Web**: [http://localhost:8000/](http://localhost:8000/)
- **Tài liệu API (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Chế độ Phát triển Frontend (Vite Dev Server)
Nếu muốn phát triển và chỉnh sửa giao diện với Hot Module Replacement (HMR):
```bash
cd frontend
npm run dev
```
Truy cập: [http://localhost:5173/](http://localhost:5173/) (Vite dev server sẽ tự động proxy các request `/api` và `/ws` về backend port `8000`).

---

## 🧪 Các Thí nghiệm trong Use Case Greenhouse

1. **Thí nghiệm 1: Accuracy & Convergence (`exp1_accuracy`)**
   - Đánh giá độ chính xác và tốc độ hội tụ của thuật toán GA khi hiệu chỉnh Model B so với tập dữ liệu tham chiếu Model A.
   - Lệnh chạy: `uv run python cases/greenhouse/exp1_accuracy.py`

2. **Thí nghiệm 2: Multi-Scenario Validation (`exp2_scenarios`)**
   - Đánh giá khả năng thích ứng của Model B đã hiệu chỉnh qua các mùa, thời tiết cực đoan (nắng nóng, lạnh giá) và dịch chuyển phụ tải.
   - Lệnh chạy: `uv run python cases/greenhouse/exp2_scenarios.py`

3. **Thí nghiệm 3: Degradation & Recalibration (`exp3_degradation`)**
   - Mô phỏng hiện tượng rách bạt (tăng rò rỉ khí tự nhiên) và suy giảm hiệu suất tấm pin PV, kích hoạt tái hiệu chuẩn thích ứng.
   - Lệnh chạy: `uv run python cases/greenhouse/exp3_degradation.py`
