# Vietnamese Sentiment Analysis

Phân tích cảm xúc văn bản tiếng Việt sử dụng PhoBERT. Dataset: UIT-VSFC / VMTEB.

## Cấu trúc dự án

```
vietnamese-sentiment-analysis/
├── backend/           # REST API (FastAPI)
│   ├── app/
│   │   ├── api/       # Routes: auth, feedbacks, dashboard giảng viên, admin…
│   │   ├── core/      # Config, JWT, đường dẫn model
│   │   ├── db/        # SQLite (users, classes, feedbacks)
│   │   ├── schemas/
│   │   └── services/  # PhoBERT, import Excel, thống kê
│   ├── requirements.txt
│   ├── run.py
│   ├── .env.example      # Mẫu JWT_SECRET_KEY + ADMIN_API_KEY → copy thành .env
│   └── .env              # Tạo cục bộ, không commit (gitignore)
├── frontend/
│   ├── index.html              # Demo gọi API (cần JWT)
│   ├── student.html            # Cổng sinh viên (khảo sát + lịch sử)
│   ├── lecturer.html           # Dashboard giảng viên (biểu đồ + quản lý phản hồi)
│   ├── js/                     # student-portal.js, teacher-dashboard.js, portal.js
│   └── styles/                 # portal.css, student.css, teacher-dashboard.css
├── data/
│   ├── models/phobert_sentiment/   # Model PhoBERT
│   └── users.db                    # SQLite (tạo khi chạy backend, có thể gitignore)
└── README.md
```

---

## Khởi động Backend

### Yêu cầu

- Python 3.10+ (khuyến nghị)
- Đủ dung lượng để cài PyTorch / transformers (lần đầu có thể lâu)

### Các bước

1. **Cài dependency** (nên dùng venv):

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **File `backend/.env`** (khuyến nghị): sao chép `backend/.env.example` → `backend/.env` rồi chỉnh hai khóa **`JWT_SECRET_KEY`** (ký JWT) và **`ADMIN_API_KEY`** (header `X-Admin-Key` cho import Excel / tạo lớp). Backend tự nạp file này khi khởi động (`python-dotenv`). File `.env` đã nằm trong `.gitignore` — không commit. Nếu chưa có `.env`, JWT vẫn có giá trị mặc định trong code; `ADMIN_API_KEY` rỗng thì hai endpoint admin trả 503 cho đến khi bạn cấu hình.

3. **Model PhoBERT** phải có trong `data/models/phobert_sentiment/` (xem mục [Model](#3-model) bên dưới).

4. **Chạy API** (một trong hai cách):

   Từ thư mục `backend`:

   ```bash
   cd backend
   python run.py
   ```

   `python run.py` **không** bật `--reload` (một process, tránh lỗi model trên Windows). Cần reload khi sửa code: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (chỉ dùng khi dev).

   Hoặc **từ thư mục gốc dự án** (không cần `cd backend`):

   ```bash
   python backend/run.py
   ```

   Lệnh `python run.py` **không** kèm đường dẫn thì chỉ chạy được khi terminal đang ở trong `backend/`.

   Hoặc dùng uvicorn **sau khi** `cd backend`:

   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Địa chỉ mặc định:** http://localhost:8000  
   - Swagger UI: http://localhost:8000/docs  
   - Health: http://localhost:8000/health  

### Biến môi trường (tuỳ chọn)

| Biến | Mô tả |
|------|--------|
| `PORT` | Cổng khi chạy `python run.py` (mặc định `8000`). Khi 10048 (*port in use*): tắt server cũ, hoặc `PORT=8002` và đổi `API_URL` trong các file `frontend/js/*.js` cho khớp. |
| `JWT_SECRET_KEY` | Khóa ký JWT (production bắt buộc đổi) |
| `JWT_EXPIRE_MINUTES` | Thời hạn token (mặc định ~7 ngày) |
| `DEFAULT_INITIAL_PASSWORD` | Mật khẩu **ban đầu** cho mọi user tạo bằng seed và **import Excel** (mặc định `Huce@123`). Cột password trong file Excel **bị bỏ qua**. |
| `ADMIN_API_KEY` | Khóa cho `POST /admin/classes`, `POST /admin/users/import-excel`, `POST /admin/import-master-excel` (header `X-Admin-Key`). Nếu để trống, các endpoint này trả **503**. |

### Khóa quản trị (`ADMIN_API_KEY` và header `X-Admin-Key`)

#### Endpoint nào cần khóa?

Các API sau yêu cầu header **`X-Admin-Key`** trùng với giá trị **`ADMIN_API_KEY`** trên server:

| Phương thức | Đường dẫn | Mô tả |
|-------------|-----------|--------|
| `POST` | `/admin/classes` | Tạo một lớp nếu chưa có (khớp `class_name` + `department`). |
| `POST` | `/admin/users/import-excel` | Upload **một sheet** `.xlsx` / `.xlsm`: danh sách user có cột `role`. Mật khẩu ban đầu = `DEFAULT_INITIAL_PASSWORD` (`Huce@123` mặc định); **không** đọc cột password từ file. |
| `POST` | `/admin/import-master-excel` | Upload **ba sheet** trong một file: **Subjects**, **Classes**, **Users** (sinh viên). Hệ thống nhận diện sheet theo **tiêu đề cột**, tên sheet đặt tùy ý. |

**Lưu ý:** Thống kê / bảng phản hồi giảng viên (`/admin/stats/...`, `/admin/feedbacks/...`, …) chỉ cần **JWT** (đăng nhập cổng **teacher** trên `lecturer.html`), **không** dùng `X-Admin-Key`.

#### Lỗi **404** khi upload Excel

- **Khởi động lại backend** sau khi cập nhật code: `python run.py` mặc định **không** tự reload; process cũ có thể chưa có route mới.
- Dev có thể bật reload: `UVICORN_RELOAD=1 python run.py` (xem `backend/run.py`).
- Kiểm tra nhanh: mở trình duyệt [http://localhost:8000/admin/import-master-excel](http://localhost:8000/admin/import-master-excel) (GET) — nếu thấy JSON `{ "ok": true, ... }` thì route tồn tại; nếu **404** thì server đang chạy bản cũ hoặc sai cổng (`PORT` / `API_URL` ở frontend).
- Đuôi file đúng là **`.xlsx`** hoặc **`.xlsm`**, không phải `.xlxs`.

#### File Excel 3 sheet (`POST /admin/import-master-excel`)

Hệ thống **nhận diện từng sheet theo tiêu đề cột** (dòng 1), **không** bắt buộc đặt tên sheet là `Subjects` / `Classes` / `Users`. Thứ tự sheet trong file có thể tùy ý (ví dụ Sheet1 = môn, Sheet2 = sinh viên, Sheet3 = lớp).

**Mẫu chuẩn (theo spec dự án):**

| Sheet (gợi ý) | Mục đích | Cột bắt buộc (dòng 1) | Ghi chú |
|---------------|----------|------------------------|---------|
| **Sheet 1 — Subjects** | Danh mục môn (nguồn tích chọn trên trang giảng viên) | `subject_code`, `subject_name` | Cột **`Ghi chú`** (hoặc tương tự) **bỏ qua**. Mỗi mã môn unique; môn được gắn vào **mọi kỳ** đã có trong DB. |
| **Sheet 3 — Classes** | Danh mục lớp | `class_name`, `department` | **Không** có cột MSSV/username (tránh nhầm sheet Users). |
| **Sheet 2 — Users** | Danh sách sinh viên | `username` hoặc **`username (MSSV)`** hoặc `MSSV`, `full_name`, `class_name` | Giá trị cột MSSV = **tài khoản đăng nhập**. **`class_name` phải trùng y hệt** `class_name` trên sheet lớp (vd. `65KTPM1`). Cột **`password (mặc định)`** trong file **không dùng**; mật khẩu lần đầu = **`DEFAULT_INITIAL_PASSWORD`** (mặc định **`Huce@123`**). |

**Ví dụ dữ liệu (rút gọn):**

- **Subjects:** `IT4440` / PhoBERT và Ứng dụng NLP; `IT3011` / Lập trình Python nâng cao; `IT2020` / Cơ sở dữ liệu; …
- **Classes:** `65KTPM1` — Khoa Công nghệ thông tin; `65KTPM2` — …; `65HTTT1` — …
- **Users:** MSSV `20210001`, họ tên, lớp `65KTPM1` (trùng sheet lớp); mật khẩu trong ô Excel có thể để trống hoặc bất kỳ — server vẫn gán `Huce@123` khi import.

Tiêu đề tiếng Việt có dấu, dạng **`username (MSSV)`**, lỗi **`(full_name`**, **`class_nam`** đều được chuẩn hóa tự động. Nên định dạng cột MSSV kiểu **Văn bản (Text)** trong Excel.

#### Hành vi khi chưa cấu hình hoặc sai khóa

- **`ADMIN_API_KEY` để trống** trên server → các endpoint admin có khóa trên trả **503** với nội dung kiểu *Chưa cấu hình ADMIN_API_KEY trên server*.
- **Có cấu hình** nhưng request **thiếu header** hoặc **sai giá trị** → **403** (*Khóa quản trị không hợp lệ*).

#### Cách tạo giá trị khóa

Dùng **chuỗi bí mật đủ dài** (khuyến nghị ≥ 32 ký tự), **không** đưa vào Git. Gợi ý tạo nhanh:

- **PowerShell:**  
  `"dev-" + [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")`
- **Git Bash** (nếu có OpenSSL):  
  `openssl rand -hex 32`

#### Cách đặt `ADMIN_API_KEY` trên máy chủ (rồi chạy lại backend)

**Cách ưu tiên:** đặt giá trị trong **`backend/.env`** (đã hỗ trợ tự nạp khi chạy app).

Hoặc đặt biến môi trường **trước** khi chạy `python run.py` / uvicorn (ghi đè `.env` nếu trùng tên biến):

**Windows CMD** (cùng cửa sổ, rồi chạy server):

```bat
set ADMIN_API_KEY=chuoi_bi_mat_cua_ban
cd backend
python run.py
```

**Windows PowerShell:**

```powershell
$env:ADMIN_API_KEY = "chuoi_bi_mat_cua_ban"
cd backend
python run.py
```

**Git Bash:**

```bash
export ADMIN_API_KEY='chuoi_bi_mat_cua_ban'
cd backend
python run.py
```

Đổi `chuoi_bi_mat_cua_ban` thành khóa bạn đã tạo. **Khởi động lại** backend mỗi khi đổi giá trị biến.

#### Gửi `X-Admin-Key` khi gọi API (curl / Swagger)

Header HTTP:

- Tên: **`X-Admin-Key`**
- Giá trị: **đúng y hệt** `ADMIN_API_KEY` trên server (có phân biệt khoảng trắng đầu/cuối nếu bạn lỡ thêm — nên không thêm).

Ví dụ **tạo lớp**:

```bash
curl -X POST "http://localhost:8000/admin/classes" ^
  -H "Content-Type: application/json" ^
  -H "X-Admin-Key: chuoi_bi_mat_cua_ban" ^
  -d "{\"class_name\":\"KTPM 01\",\"department\":\"Khoa CNTT\"}"
```

(Trên Git Bash dùng `\` thay `^` để xuống dòng, hoặc ghi một dòng.)

Trên **Swagger** (`/docs`): mở endpoint tương ứng → bấm **Try it out** → thêm header tùy chỉnh **`X-Admin-Key`** nếu giao diện cho phép, hoặc dùng curl/Postman.

#### Trên giao diện giảng viên (`lecturer.html`)

1. Đăng nhập cổng **teacher**.
2. Vào tab **Quản trị**.
3. Ô **Khóa quản trị (X-Admin-Key)**: dán **cùng** giá trị với `ADMIN_API_KEY` đã set trên server → **Lưu** (lưu trong `sessionStorage` của trình duyệt).
4. Sau đó mới dùng **Import Excel** / **Tạo lớp** trên cùng trang.

#### Bảo mật

- Không commit `ADMIN_API_KEY` lên kho mã.
- Production: khóa mạnh, chỉ cấp cho người được phép; đổi khóa khi nghi lộ.

### CSDL

- SQLite: `data/users.db` (tạo tự động khi khởi động).
- Chỉ khi **chưa có bất kỳ user nào** trong CSDL, backend tự seed các tài khoản demo bên dưới (mật khẩu = giá trị `DEFAULT_INITIAL_PASSWORD`, mặc định `Huce@123`). Nếu đã có user (ví dụ sau import Excel), seed **không** chạy lại — xóa `data/users.db` nếu cần reset môi trường dev.

#### Tài khoản demo (cho thầy cô test)

| Vai trò | Đăng nhập (MSSV / mã) | Họ tên | Lớp | Cổng | Mật khẩu mặc định | Ghi chú |
|---------|------------------------|--------|-----|------|-------------------|---------|
| Sinh viên | `38165` | Sinh viên Demo | KTPM — Demo (Khoa Công nghệ thông tin) | **student** — trang `frontend/student.html` (khuyến nghị mở qua static server cổng 3000) | `Huce@123` (hoặc giá trị `DEFAULT_INITIAL_PASSWORD`) | Lần đầu đăng nhập hệ thống yêu cầu **đổi mật khẩu** trước khi dùng khảo sát đầy đủ. |
| Giảng viên | `gv.demo` | Giảng viên Demo | — | **teacher** — trang `frontend/lecturer.html` | Cùng mật khẩu mặc định như trên | Không bị ép đổi mật khẩu; dùng để xem dashboard, bảng phản hồi và (nếu cấu hình `ADMIN_API_KEY`) quản trị import. |

#### Đăng nhập sinh viên báo 401 (sai tên đăng nhập hoặc mật khẩu)

- Đảm bảo mở **`student.html`** (cổng **student**), không dùng tài khoản sinh viên trên **`lecturer.html`** (teacher).
- Mật khẩu phải trùng **`DEFAULT_INITIAL_PASSWORD`** trong `backend/.env` (mặc định `Huce@123`). Nếu trước đó import Excel khi còn đọc cột password riêng, hash trong DB có thể **không** phải `Huce@123` → vẫn 401. **Cách xử lý (dev):** chạy từ thư mục `backend`:

  ```bash
  python scripts/rehash_student_passwords.py
  ```

  Script đặt lại mật khẩu **mọi** tài khoản `role = student` theo giá trị `DEFAULT_INITIAL_PASSWORD` hiện tại. Hoặc **import lại** master Excel (upsert sẽ cập nhật hash).

- `frontend/js/student-portal.js` dùng `API_URL = 'http://localhost:8000'` — nếu backend chạy cổng khác (`PORT`), đổi cho khớp.

---

## Khởi động Frontend

Giao diện là file HTML tĩnh gọi API tại **`http://localhost:8000`**. Cần **bật backend trước** (và CORS mặc định đã mở cho dev).

### Cách 1: Mở file trực tiếp

- Mở trong trình duyệt: `frontend/student.html`, `frontend/lecturer.html`, hoặc `frontend/index.html`.  
- Một số trình duyệt có thể hạn chế `fetch` từ `file://`; nếu lỗi, dùng Cách 2.

### Cách 2: Static server (khuyến nghị)

```bash
cd frontend
python -m http.server 3000
```

Truy cập:

| URL | Mô tả |
|-----|--------|
| http://localhost:3000/student.html | Cổng sinh viên: đăng nhập, khảo sát (gửi phản hồi + PhoBERT), lịch sử |
| http://localhost:3000/lecturer.html | Dashboard giảng viên: thống kê, biểu đồ, bảng phản hồi, quản trị (import Excel / tạo lớp cần `ADMIN_API_KEY`) |
| http://localhost:3000/index.html | Demo gọi `/predict` (cần JWT sau khi đăng nhập cổng SV/GV) |

### Cấu hình API URL

- Mặc định trong `js/student-portal.js`, `js/teacher-dashboard.js`, `js/index.html` (và `portal.js`): `http://localhost:8000`.  
- Nếu backend chạy host/port khác, sửa hằng `API_URL` / chuỗi tương ứng trong các file đó.

---

## API Endpoints (tóm tắt)

| Method | Endpoint | Mô tả |
|--------|----------|--------|
| GET | `/health` | Trạng thái API / model |
| POST | `/auth/login` | Đăng nhập JWT (`portal`: `student` \| `teacher`) |
| GET | `/users/me` | Hồ sơ + lớp (header Bearer) |
| POST | `/feedbacks` | Sinh viên gửi phản hồi (PhoBERT + lưu DB) |
| GET | `/feedbacks/my-history` | Lịch sử phản hồi sinh viên |
| POST | `/predict`, `/preprocess` | Phân tích (cần Bearer, sinh viên phải đổi mật khẩu nếu bắt buộc) |
| GET | `/admin/stats/overview`, `/admin/stats/classes` | Thống kê (JWT **giảng viên**) |
| GET | `/admin/feedbacks/all` | Bảng phản hồi + lọc + `q` tìm kiếm |
| GET | `/admin/feedbacks/alerts` | Top phản hồi tiêu cực |
| POST | `/admin/classes`, `/admin/users/import-excel` | Quản trị (**X-Admin-Key**) |

Chi tiết đầy đủ: **http://localhost:8000/docs**

**Ví dụ** (cần token sau khi đăng nhập):

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"text": "Sản phẩm rất tốt, giao hàng nhanh!"}'
```

---

## Model

Model đặt trong `data/models/phobert_sentiment/`. Nếu chưa có, tải từ [Google Drive](https://drive.google.com/drive/folders/10fTSurdv9Mu6nBmLc_elrWhfgOJzlUAh) và giải nén vào thư mục trên.

---

## Pipeline

1. **Chuẩn hóa**: Unicode NFC, loại bỏ khoảng trắng thừa  
2. **Tách từ**: Underthesea `word_tokenize`  
3. **Dự đoán**: PhoBERT (RobertaForSequenceClassification, 3 lớp: negative, neutral, positive)

---

## Colab & Model

- [Colab notebook](https://colab.research.google.com/drive/1B1p755q0-Qf67USj8ku1W3hPCzHaUZu9)
- Dataset: [another-symato/VMTEB-vietnamese_students_feedback_sentiment_word_segment](https://huggingface.co/datasets/another-symato/VMTEB-vietnamese_students_feedback_sentiment_word_segment)
