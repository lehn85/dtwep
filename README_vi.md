# Digital Twin with EnergyPlus (DTWEP)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](Licence.txt)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite%20%7C%20TypeScript-61dafb.svg)](https://react.dev)
[![Standard](https://img.shields.io/badge/Standard-ASHRAE%20Guideline%2014-success.svg)](https://www.ashrae.org)

**[English](README.md)** | **[Tiếng Việt](README_vi.md)**

---

## 📌 Tổng quan

**Digital Twin with EnergyPlus (DTWEP)** là một khung làm việc (framework) mã nguồn mở, có tính mở rộng cao phục vụ mô phỏng đồng thời (co-simulation), tự động hiệu chuẩn tham số (automated calibration), kiểm định chéo đa kịch bản (multi-scenario cross-validation) và theo dõi suy thoái vật lý cho công trình năng lượng. Hệ thống kết nối các công cụ mô phỏng vật lý có độ trung thực cao (EnergyPlus / OpenStudio) với mô hình đại diện Digital Twin bậc thấp, siêu nhanh, tối ưu hóa cho điện toán biên và giám sát vận hành thời gian thực.

DTWEP được thiết kế theo kiến trúc **Multi-Case Platform** có khả năng tự động khám phá và cắm/rút ca nghiên cứu. Trường hợp ứng dụng mẫu là mô hình **Nhà kính Nông điện Răng cưa (Agrivoltaic Sawtooth Greenhouse)** tại Buôn Ma Thuột, Việt Nam, tích hợp vi khí hậu nhà kính, rò rỉ khí thông gió tự nhiên, hệ thống phát điện mặt trời áp mái (PV) và hệ thống lưu trữ năng lượng pin (BESS).

### Vấn đề cốt lõi & Khái niệm
- **Model A (Mô hình Tham chiếu / Ground Truth)**: Mô hình OpenStudio/EnergyPlus đa vùng (multi-zone), chi tiết về mặt hình học, mô phỏng đổ bóng kết cấu phức tạp, phân bố bức xạ 3D và thông gió tự nhiên. Dù có độ chính xác cao nhưng thời gian mô phỏng dài (~20–40 giây/bước chạy), không khả thi cho điều khiển biên thời gian thực.
- **Model B (Mô hình Digital Twin Rút gọn)**: Mô hình nhiệt đơn vùng (single-zone lumped model) bậc thấp, tốc độ tính toán siêu nhanh (~0.5–1.5 giây/bước chạy).
- **Bộ máy Hiệu chuẩn Giải thuật Di truyền (GA)**: Tự động tinh chỉnh các tham số nhiệt vỏ bao và hệ thống điện của Model B dựa trên dữ liệu mục tiêu của Model A nhằm đạt chuẩn quốc tế **ASHRAE Guideline 14**.
- **Theo dõi Suy thoái Vật lý & Tái hiệu chuẩn**: Mô phỏng sự xuống cấp theo thời gian (như rách màng bạt gây tăng rò rỉ khí, bám bụi/suy giảm hiệu suất tấm pin PV), tự động nhận diện sai số lệch chuẩn và kích hoạt chu trình tái hiệu chuẩn thích ứng.

---

## 🌟 Tính năng nổi bật

1. **Bộ máy Tự động Hiệu chuẩn (Automated Calibration Engine)**:
   - Thuật toán di truyền đa mục tiêu (Multi-objective Genetic Algorithm - GA) với khả năng tùy biến kích thước quần thể, số thế hệ, xác suất lai ghép/đột biến và cơ chế tinh hoa (elitism).
   - Tối ưu hóa đồng thời các biến trạng thái: nhiệt độ vùng, độ ẩm, bức xạ mặt trời trong nhà và công suất điện lưới/pin.
   - Xuất biểu đồ hội tụ chất lượng cao và ghi nhật ký tiến trình từng thế hệ.

2. **Đánh giá Tuân thủ Chuẩn ASHRAE Guideline 14 & Hệ chỉ số Đa quy mô**:
   - Tự động tính toán **Normalized Mean Bias Error (NMBE)** ($\le \pm 10\%$ theo giờ), **Coefficient of Variation of Root Mean Square Error (CVRMSE)** ($\le 30\%$ theo giờ), và **Hệ số xác định ($R^2$)** ($\ge 0.70$).
   - Quy đổi nhiệt độ về thang nhiệt động học Kelvin ($T_K = T_C + 273.15$) khi tính các chỉ số phần trăm, ngăn ngừa méo số học do điểm không (zero-crossing).
   - Bổ sung các chỉ số thống kê tiêu chuẩn: MAE, RMSE, MAPE.

3. **Kiến trúc Tự động Khám phá Đa Use-case (Multi-Case Auto-Discovery)**:
   - Tách biệt hoàn toàn giữa thư viện lõi (`calibration_framework/`) và các use case cụ thể (`cases/`).
   - Tự động nhận diện cấu hình case thông qua tệp đặc tả `case.yaml` (danh mục mô hình, danh sách thí nghiệm, tệp cấu hình mặc định).

4. **Bộ Chuyển đổi Mô phỏng Linh hoạt (Simulation Adapters)**:
   - Tự động chuyển đổi giữa OpenStudio (`.osm`) và EnergyPlus (`.idf`).
   - Cung cấp dữ liệu thực tế (Ground Truth) đa dạng: mô phỏng số, tệp chuỗi thời gian CSV, cảm biến đo đạc vật lý hoặc REST API từ xa.
   - Nguồn dữ liệu thời tiết linh hoạt: tệp thời tiết EPW, dữ liệu thời tiết nhiễu nhân tạo và trạm khí tượng.

5. **Giao diện Web Đầy đủ (Full-Stack SPA) & Giám sát Thời gian thực**:
   - **Backend**: FastAPI hiệu năng cao, cung cấp REST APIs và kết nối WebSocket (`/ws/run`) truyền phát log terminal trực tiếp cùng tiến trình tối ưu GA theo thời gian thực.
   - **Frontend**: Ứng dụng Single-Page Application (SPA) phong cách Dark Glassmorphic hiện đại, xây dựng bằng React 18, Vite, TypeScript, Tailwind CSS và Recharts.
   - **Trình soạn thảo Cấu hình Kép (Dual Config Editor)**: Chuyển đổi linh hoạt giữa giao diện biểu mẫu thanh trượt (Sliders) trực quan và trình biên tập mã nguồn YAML có kiểm tra lỗi cú pháp thời gian thực.
   - **Phân tích Trực quan**: Biểu đồ chuỗi thời gian tương tác so sánh Model A & Model B kèm biểu đồ sai số dư (residuals), bảng trạng thái đạt chuẩn ASHRAE và thư viện ảnh đồ thị phóng to Lightbox.

---

## 🏗️ Cấu trúc Thư mục Dự án

```
digital-twin-with-energy-plus/
├── app/                                 # Dịch vụ backend ứng dụng Web
│   ├── case_manager.py                  # Quản lý quét ca nghiên cứu, cấu hình và kết quả
│   ├── experiment_runner.py             # Quản lý tiến trình chạy thí nghiệm
│   └── module_runner.py                 # Bộ thực thi tác vụ bất đồng bộ & stream WebSocket
├── calibration_framework/               # Khung thư viện lõi hiệu chuẩn & đồng mô phỏng
│   ├── engine.py                        # Bộ điều phối quy trình hiệu chuẩn
│   ├── evaluator.py                     # Hàm mục tiêu & đánh giá mất mát đa mục tiêu
│   ├── ground_truth.py                  # Các nhà cung cấp Ground Truth (Simulation, CSV, API)
│   ├── metrics.py                       # Thư viện tính toán sai số & kiểm tra chuẩn ASHRAE 14
│   ├── model_adapter.py                 # Bộ chuyển đổi & can thiệp mô hình OpenStudio / EnergyPlus
│   ├── plotting.py                      # Bộ sinh đồ thị chuẩn công bố khoa học
│   ├── runner.py                        # Trình chạy EnergyPlus & trích xuất kết quả từ SQLite
│   ├── schemas.py                       # Định nghĩa lược đồ dữ liệu & cấu hình Pydantic
│   ├── timeseries.py                    # Căn chỉnh & hậu xử lý chuỗi thời gian
│   ├── weather.py                       # Phân tích tệp EPW & tạo dữ liệu thời tiết nhân tạo
│   ├── experiments/                     # Các lớp cơ sở của các bài thí nghiệm chuẩn
│   │   ├── base.py                      # Vòng đời thực thi thí nghiệm
│   │   ├── exp1_initial_calibration.py  # Logic cốt lõi Thí nghiệm 1
│   │   ├── exp2_scenario_simulation.py  # Logic cốt lõi Thí nghiệm 2
│   │   └── exp3_recalibration.py        # Logic cốt lõi Thí nghiệm 3
│   └── optimizers/                      # Các thuật toán tối ưu hóa
│       ├── base.py                      # Giao diện cơ sở thuật toán tối ưu
│       └── genetic_algorithm.py         # Triển khai thuật toán di truyền (GA)
├── cases/                               # Thư mục chứa các ca nghiên cứu (Use cases)
│   └── greenhouse/                      # Ca nghiên cứu Nhà kính Nông điện Răng cưa
│       ├── case.yaml                    # Siêu dữ liệu ca nghiên cứu, mô hình và danh mục thí nghiệm
│       ├── models/                      # Mô hình OpenStudio gốc ban đầu (greenhouse_sawtooth.osm)
│       ├── weather/                     # Bộ tệp dữ liệu thời tiết EnergyPlus (EPW) của ca
│       ├── adapters.py                  # Bộ ánh xạ tham số chuyên biệt cho nhà kính
│       ├── geometry.py                  # Trình sinh hình học tham số cho OpenStudio
│       ├── model_transform.py           # Mở rộng Model A và rút gọn sang Model B
│       ├── scenarios.py                 # Định nghĩa các kịch bản thời tiết & vận hành
│       ├── exp1_initial_calibration.py  # Tệp thực thi Thí nghiệm 1
│       ├── exp2_scenario_simulation.py  # Tệp thực thi Thí nghiệm 2
│       ├── exp3_recalibration.py        # Tệp thực thi Thí nghiệm 3
│       └── configs/                     # Các tệp cấu hình YAML
│           ├── calibration.yaml         # Miền tìm kiếm GA, siêu tham số và trọng số
│           ├── exp1_initial_calibration.yaml
│           ├── exp2_scenario_simulation.yaml
│           └── exp3_recalibration.yaml
├── frontend/                            # Mã nguồn giao diện Web React + Vite + TypeScript
│   ├── src/                             # Thành phần UI, dịch vụ gọi API và kiểu dữ liệu
│   ├── dist/                            # Bản build production được FastAPI phục vụ
│   └── package.json                     # Quản lý phụ thuộc & scripts của frontend
├── results/                             # Kết quả đầu ra của thí nghiệm, bảng CSV và đồ thị
│   └── greenhouse/models/               # Các mô hình mở rộng OSM/IDF và Model B sinh tự động (được git bỏ qua)
├── run_greenhouse_experiments.ps1       # Script PowerShell tương tác chạy thí nghiệm (Windows)
├── run_greenhouse_experiments.sh        # Script Bash tương tác chạy thí nghiệm (Linux/macOS)
├── main.py                              # Server chính FastAPI (REST API, WebSocket, SPA host)
├── pyproject.toml                       # Cấu hình dự án Python & danh sách thư viện phụ thuộc
├── Licence.txt                          # Bản quyền phần mềm GNU General Public License v3.0
└── README_vi.md                         # Tài liệu hướng dẫn dự án (Tiếng Việt)
```

---

## 💻 Yêu cầu Hệ thống & Điều kiện Tiên quyết

### Phần cứng
- **Bộ vi xử lý (CPU)**: Đa nhân (Khuyến nghị Intel Core i5/i7/i9 hoặc AMD Ryzen 5/7/9, tối thiểu 4 nhân vật lý để mô phỏng song song).
- **Bộ nhớ trong (RAM)**: Tối thiểu 8 GB (Khuyến nghị 16 GB).
- **Dung lượng đĩa trống**: Tối thiểu 2 GB cho bộ nhớ đệm mô phỏng và cơ sở dữ liệu SQLite sinh ra trong quá trình chạy.

### Phần mềm & Hệ điều hành
- **Hệ điều hành**: Windows 10/11, Ubuntu 20.04/22.04 LTS, hoặc macOS 12+.
- **Python**: Phiên bản $\ge 3.12$.
- **Bộ quản lý gói Python**: [uv](https://docs.astral.sh/uv/) (khuyên dùng để cài đặt nhanh chóng và đồng nhất môi trường).
- **Node.js**: Phiên bản $\ge 18.0.0$ cùng npm (cần thiết để biên dịch giao diện người dùng).
- **Bộ máy Mô phỏng Năng lượng Tòa nhà**:
  - `openstudio` ($\ge 3.8.0$)
  - `pyenergyplus-lbnl` ($\ge 24.0.0$ / được quản lý tự động qua `pyproject.toml`)

---

## 📦 Hướng dẫn Cài đặt & Thiết lập

### 1. Sao chép Mã nguồn (Clone Repository)
```bash
git clone https://github.com/lehn85/digital-twin-with-energy-plus.git
cd digital-twin-with-energy-plus
```

### 2. Thiết lập Môi trường Python với `uv`
Khởi tạo môi trường ảo và cài đặt toàn bộ thư viện:
```bash
# Cài đặt uv nếu máy tính chưa có (https://docs.astral.sh/uv/)
# Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS: curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
```

### 3. Biên dịch Giao diện Người dùng (Frontend)
Biên dịch ứng dụng React thành các tệp tĩnh nằm trong `frontend/dist/`:
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 🚀 Khởi chạy & Sử dụng Nhanh

### Cách 1: Giao diện Web Trực quan (Khuyến nghị)

Khởi động máy chủ ứng dụng FastAPI:
```bash
uv run python main.py
```
Hoặc khởi chạy qua Uvicorn:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Sau khi máy chủ khởi động thành công:
- **Giao diện Web**: Truy cập [http://localhost:8000/](http://localhost:8000/) trên trình duyệt.
- **Tài liệu API tương tác (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs).
- **Tài liệu API thay thế (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc).

#### Chế độ Phát triển Frontend (Hot Reload)
Nếu bạn muốn chỉnh sửa giao diện frontend với tính năng cập nhật tức thì (HMR):
```bash
cd frontend
npm run dev
```
Truy cập [http://localhost:5173/](http://localhost:5173/). Các yêu cầu API và WebSocket sẽ tự động được proxy về cổng `8000`.

---

### Cách 2: Chạy Thí nghiệm từ Dòng lệnh (CLI)

Dự án cung cấp sẵn các tệp kịch bản tự động hóa để chạy từng thí nghiệm hoặc toàn bộ quy trình:

#### Trên Windows (PowerShell):
```powershell
# Chạy menu tương tác:
.\run_greenhouse_experiments.ps1

# Hoặc chỉ định trực tiếp bài thí nghiệm:
.\run_greenhouse_experiments.ps1 -Choice 1   # Thí nghiệm 1
.\run_greenhouse_experiments.ps1 -Choice 2   # Thí nghiệm 2
.\run_greenhouse_experiments.ps1 -Choice 3   # Thí nghiệm 3
.\run_greenhouse_experiments.ps1 -Choice 5   # Chạy tuần tự tất cả các bài
```

#### Trên Linux / macOS (Bash):
```bash
chmod +x run_greenhouse_experiments.sh

# Chạy menu tương tác:
./run_greenhouse_experiments.sh

# Hoặc chạy trực tiếp:
./run_greenhouse_experiments.sh 1            # Thí nghiệm 1
./run_greenhouse_experiments.sh 2            # Thí nghiệm 2
./run_greenhouse_experiments.sh 3            # Thí nghiệm 3
./run_greenhouse_experiments.sh 5            # Chạy tuần tự tất cả các bài
```

#### Thực thi Trực tiếp qua Python:
```bash
# Thí nghiệm 1: Hiệu chuẩn ban đầu & Đánh giá tốc độ
uv run python cases/greenhouse/exp1_initial_calibration.py

# Thí nghiệm 2: Đánh giá chéo đa kịch bản
uv run python cases/greenhouse/exp2_scenario_simulation.py

# Thí nghiệm 3: Theo dõi suy thoái vật lý & Tái hiệu chuẩn
uv run python cases/greenhouse/exp3_recalibration.py
```

---

## 🧪 Chi tiết Các Thí nghiệm Chuẩn (Benchmarks)

Hệ thống cung cấp 3 thí nghiệm benchmark chính cho mô hình Nhà kính Nông điện:

| Thí nghiệm | Tệp kịch bản | Cấu hình | Mục tiêu chính | Các chỉ số đánh giá cốt lõi |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1: Hiệu chuẩn ban đầu** | `cases/greenhouse/exp1_initial_calibration.py` | `exp1_initial_calibration.yaml` | Hiệu chuẩn Model B theo Model A tham chiếu bằng giải thuật di truyền GA | NMBE, CVRMSE, $R^2$, Hệ số tăng tốc độ tính toán (Speedup) |
| **Exp 2: Đánh giá Đa kịch bản** | `cases/greenhouse/exp2_scenario_simulation.py` | `exp2_scenario_simulation.yaml` | Kiểm định chéo độ bền vững của Model B qua các điều kiện thời tiết & vận hành khác biệt | Sai số NMBE, CVRMSE đa kịch bản, Phân bố phần dư |
| **Exp 3: Theo dõi Suy thoái** | `cases/greenhouse/exp3_recalibration.py` | `exp3_recalibration.yaml` | Phát hiện biến đổi vật lý (rách màng bạt & suy giảm quang điện) và tái hiệu chuẩn | Độ lệch chỉ số thống kê, Tốc độ hội tụ khi tái hiệu chuẩn |

### 1. Thí nghiệm 1: Initial Calibration Benchmark
- **Mục tiêu**: Tinh chỉnh các thông số vật lý của Model B (hệ số truyền nhiệt U-factor của kính, hệ số hấp thụ nhiệt mặt trời SHGC, tỷ lệ rò rỉ khí thông gió, độ dẫn nhiệt nền đất, hiệu suất pin mặt trời PV) để đầu ra mô phỏng tiệm cận Model A.
- **Tệp kết quả đầu ra**:
  - `results/greenhouse/exp1_initial_calibration/metrics.csv`: Bảng chỉ số sai số ASHRAE cho nhiệt độ, độ ẩm, bức xạ trong nhà, nhiệt độ mặt kính, công suất lưới và công suất PV.
  - `convergence_curve.png`: Đồ thị theo dõi độ thích nghi tốt nhất và trung bình qua các thế hệ GA.
  - `timeseries_comparison.png`: So sánh chuỗi thời gian hàng giờ giữa Model A và Model B kèm đồ thị sai số dư.
  - `computational_performance.png`: Biểu đồ so sánh thời gian thực thi và hệ số tăng tốc.

### 2. Thí nghiệm 2: Multi-Scenario Cross-Validation
- **Mục tiêu**: Đánh giá độ tin cậy và khả năng khái quát hóa của Model B đã hiệu chỉnh trong các điều kiện làm việc mới mà không cần tối ưu lại tham số.
- **Các kịch bản đánh giá**:
  - Vận hành chuẩn (Standard Operation).
  - Đợt nắng nóng cực đoan (nhiệt độ bầu khô cao và cường độ bức xạ cực đại).
  - Mưa lớn và mây che phủ dày đặc.
  - Thông gió tự nhiên mở tối đa (mở toàn bộ cửa sổ thông gió).
  - Điều chỉnh phụ tải đỉnh (lịch trình xả pin tích năng BESS).
- **Tệp kết quả đầu ra**:
  - `results/greenhouse/exp2_scenario_simulation/scenario_metrics.csv`
  - `scenario_comparison.png`

### 3. Thí nghiệm 3: Physical Degradation & Adaptive Recalibration
- **Mục tiêu**: Kiểm tra năng lực tự thích ứng của bản sao số (digital twin) khi đối mặt với các biến cố hư hỏng vật lý thực tế:
  - *Rách màng bạt nhà kính*: Mô phỏng hiện tượng thủng màng polymer làm độ rò rỉ thông gió tăng gấp 3 lần.
  - *Bám bụi / Suy hao tế bào quang điện*: Mô phỏng công suất tấm pin PV giảm $25\%$.
- **Quy trình**: Hệ thống phát hiện độ lệch tiêu chuẩn thống kê, tự động kích hoạt vòng lặp hiệu chuẩn GA thích ứng và đưa các chỉ số sai số trở lại ngưỡng cho phép.
- **Tệp kết quả đầu ra**:
  - `results/greenhouse/exp3_recalibration/degradation_metrics.csv`
  - `recalibration_convergence.png`

---

## 📊 Tiêu chuẩn Tuân thủ ASHRAE Guideline 14

Nền tảng tự động đối chiếu các chuỗi thời gian mô phỏng với quy chuẩn khắt khe của **ASHRAE Guideline 14-2014**:

$$\text{NMBE} = \frac{\sum_{i=1}^{n} (y_i - \hat{y}_i)}{(n - 1) \cdot \bar{y}} \times 100\%$$

$$\text{CVRMSE} = \frac{\sqrt{\frac{1}{n - 1} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}}{\bar{y}} \times 100\%$$

$$R^2 = 1 - \frac{\sum_{i=1}^{n} (y_i - \hat{y}_i)^2}{\sum_{i=1}^{n} (y_i - \bar{y})^2}$$

Trong đó $y_i$ là giá trị mục tiêu (Model A), $\hat{y}_i$ là giá trị mô phỏng dự đoán (Model B), $\bar{y}$ là giá trị trung bình mục tiêu, và $n$ là tổng số mẫu quan sát hàng giờ.

| Chỉ số | Ngưỡng yêu cầu theo ASHRAE Guideline 14 (Bước giờ) | Trạng thái Đạt |
| :--- | :--- | :--- |
| **NMBE** | $|\text{NMBE}| \le 10.0\%$ | Đạt (Pass) |
| **CVRMSE** | $\text{CVRMSE} \le 30.0\%$ | Đạt (Pass) |
| **$R^2$** | $R^2 \ge 0.70$ | Đạt (Pass) |

> **Lưu ý đối với Biến Nhiệt độ**: Nhằm tránh hiện tượng sai số chia cho 0 hoặc giá trị gần 0 trên thang Celsius, các chỉ số tỷ lệ phần trăm (CVRMSE, NMBE) được tính toán trên thang nhiệt động lực học tuyệt đối Kelvin ($T_K = T_C + 273.15$).

---

## ⚙️ Cấu hình & Tùy biến Hệ thống

Toàn bộ các tham số vật lý, không gian tìm kiếm và thiết lập mô phỏng được định nghĩa trong các tệp YAML có cấu trúc rõ ràng.

### Tệp Cấu hình Hiệu chuẩn (`cases/greenhouse/configs/calibration.yaml`)
```yaml
optimizer:
  type: "genetic_algorithm"
  population_size: 20
  generations: 15
  crossover_prob: 0.8
  mutation_prob: 0.2
  elite_count: 2

parameters:
  - name: "glazing_u_factor"
    target: "surface"
    min_value: 1.0
    max_value: 6.5
    default: 3.5
  - name: "infiltration_rate"
    target: "zone"
    min_value: 0.0001
    max_value: 0.0050
    default: 0.0015
  - name: "pv_efficiency"
    target: "generator"
    min_value: 0.10
    max_value: 0.24
    default: 0.18
```

### Thêm một Ca Nghiên cứu Mới (New Case Study)
1. Tạo một thư mục mới tại `cases/<id_case_mới>/`.
2. Tạo tệp `case.yaml` mô tả siêu dữ liệu, các tệp mô hình 3D (`.osm` / `.idf`), và danh sách thí nghiệm.
3. Cung cấp các bộ adapter và tệp cấu hình trong `cases/<id_case_mới>/configs/`.
4. Hệ thống sẽ tự động quét và hiển thị case mới trên giao diện web ngay khi khởi động lại.

---

## 📄 Dữ liệu Đầu ra & Tính Tái lập Nghiên cứu

Toàn bộ kết quả chạy thí nghiệm được lưu trữ lâu dài tại `results/<case_id>/<experiment_id>/`:
- `metrics.csv`: Bảng số liệu chi tiết các chỉ số thống kê sai số của tất cả các biến mục tiêu.
- `convergence.json`: Nhật ký điểm thích nghi tốt nhất và trung bình qua từng thế hệ GA.
- `best_parameters.yaml`: Bộ giá trị tham số tối ưu tìm được bởi GA.
- `plots/`: Các biểu đồ độ phân giải cao (`.png`, 300 DPI) sẵn sàng cho báo cáo khoa học:
  - `convergence_curve.png`
  - `timeseries_comparison.png`
  - `scenario_comparison.png`
  - `recalibration_comparison.png`

---

## 📜 Giấy phép Bản quyền (License)

Dự án được phân phối dưới giấy phép **GNU General Public License v3.0 (GPLv3)**. Chi tiết đầy đủ xem tại tệp [Licence.txt](Licence.txt).

---

## ✉️ Liên hệ & Hỗ trợ

Mọi thắc mắc, đóng góp mã nguồn hoặc đề xuất cải tiến:
- **Kho lưu trữ GitHub**: [https://github.com/lehn85/digital-twin-with-energy-plus](https://github.com/lehn85/digital-twin-with-energy-plus)
- **Tác giả**: lehn85 (`lehn85@gmail.com`)
