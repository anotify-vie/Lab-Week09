# Lab-Week09

* Trần Tuấn Anh - 11247264

Heroes API của Week 9 đã được bổ sung nội dung **Week 10 — REST API, JSON, Auto-Docs & Testing** từ `week10-2.pdf` và **Week 11 — Authentication & Security** từ `week11.pdf`. Xem đối chiếu Week 10 trong [WEEK10_CHECKLIST.md](WEEK10_CHECKLIST.md). Bài trả lời Week 9 vẫn nằm trong [answers.md](answers.md).

## Chạy dự án

Yêu cầu Python 3.10 trở lên. Chạy tại thư mục gốc của dự án:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

Dán chuỗi vừa tạo vào `SECRET_KEY=` trong `.env`. Giữ nguyên khóa giữa các lần chạy; `.env` được Git bỏ qua. Không dùng giá trị ví dụ làm khóa thật. `DATABASE_URL` mặc định là `sqlite:///./app.db`; có thể đổi thành `postgresql+psycopg://USER:PASSWORD@localhost:5432/DB_NAME` để dùng PostgreSQL. Biến môi trường được ưu tiên hơn `.env`.

Với database mới, chạy migration **trước khi khởi động server**:

```bash
python -m alembic upgrade head
python -m app.create_admin admin
python -m app.seed
python -m uvicorn app.main:app --reload
```

Lệnh tạo admin sẽ hỏi mật khẩu trong terminal; mật khẩu cần ít nhất 8 ký tự, không quá 72 byte UTF-8. Cũng hỗ trợ cú pháp trong slide: `python -m app.create_admin admin 'your-password'`. Chỉ CLI tạo được admin; API đăng ký luôn tạo tài khoản thường.

- Giao diện: <http://127.0.0.1:8000/frontend/>
- Swagger: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>
- API chính: `http://127.0.0.1:8000/api/v1`
- URL Week 9 như `/heroes`, `/teams` vẫn hoạt động và áp dụng cùng quyền truy cập.

`app.seed` là tùy chọn: tạo dữ liệu mẫu Week 9. Hero mẫu và hero cũ không có owner nên chỉ admin được sửa/xóa. Hero tạo qua API được gán owner từ tài khoản đang đăng nhập.

## Database đã có dữ liệu

Không cần xóa/recreate database. Bản bổ sung có baseline schema để database mới chạy được toàn bộ chuỗi migration; mã revision cũ `59b9ed58da4a` và `4158b1105b0d` được giữ lại.

Nếu database đã được Alembic quản lý:

```bash
python -m alembic current
python -m alembic upgrade head
```

Migration mới giữ hero/team/mission và các liên kết, bổ sung bảng `user`, `hero.owner_id`, `hero.created_at`; backfill `status=NULL` thành `active` rồi đặt `status` NOT NULL. Timestamp của hero cũ là thời điểm migration, vì dữ liệu trước đó chưa lưu ngày tạo.

Nếu database được tạo bằng `create_all()` và **chưa có revision Alembic**, cần xác định đúng schema trước khi `stamp`:

| Schema hiện có | Revision tương ứng |
| --- | --- |
| Hero/team/mission/link, chưa có `power` và `status` | `20261022_base` |
| Đã có `power`, chưa có `status` | `59b9ed58da4a` |
| Đã có `power` và `status`, chưa có `created_at`/`owner_id`/bảng `user` | `4158b1105b0d` |
| Schema đầy đủ được tạo mới bởi phiên bản ứng dụng này | `head` |

Chạy `python -m alembic stamp REVISION_DUNG_VOI_SCHEMA`, rồi `python -m alembic upgrade head`. `stamp` chỉ ghi nhận revision, không sửa schema. Không stamp tùy ý một database có schema khác bảng trên. `create_all()` lúc startup chỉ tạo bảng mới, không cập nhật cột của bảng đang tồn tại.

## Quyền truy cập và thử API

| Endpoint (dưới `/api/v1`) | Quyền |
| --- | --- |
| `GET /heroes`, `GET /heroes/{id}`, `GET /teams`, `GET /teams/{id}/heroes`, `GET /heroes/{id}/missions` | Công khai |
| `POST /register`, `POST /token` | Công khai |
| `GET /me`, `POST /heroes`, `POST /missions` | Đã đăng nhập |
| `PATCH /heroes/{id}`, `DELETE /heroes/{id}`, `POST /heroes/{id}/missions/{mission_id}` | Owner hoặc admin |
| `POST /teams` | Admin |

Trong `/docs`: dùng `POST /api/v1/register` để đăng ký, bấm **Authorize**, nhập username/password. Swagger gửi form đến `/api/v1/token`, rồi tự đính kèm Bearer token khi gọi endpoint bảo vệ. Có thể xem tài khoản qua `GET /api/v1/me`.

Ví dụ bằng curl:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"password123"}'

curl -i -X POST http://127.0.0.1:8000/api/v1/token \
  -d 'username=alice&password=password123'

curl -i http://127.0.0.1:8000/api/v1/me

curl -i http://127.0.0.1:8000/api/v1/me \
  -H 'Authorization: Bearer PASTE_ACCESS_TOKEN_HERE'
```

Đăng nhập gửi **form**, không gửi JSON. Token hết hạn mặc định sau 30 phút; đặt `ACCESS_TOKEN_EXPIRE_MINUTES=1` và khởi động lại server để thực hành token hết hạn. Đăng xuất xóa token ở trình duyệt; token đã phát vẫn có hiệu lực đến `exp`.

Giao diện có đăng ký, đăng nhập, “Logged in as …”, đăng xuất, xem danh sách, tạo/sửa/xóa hero và tạo team cho admin. Token lưu trong `sessionStorage`, gửi trong `Authorization` khi gọi API. Tên hero/team được đưa vào DOM bằng `textContent`/`Option`, không nội suy HTML.

## Week 10: Live Server, CORS và frontend

Có thể mở giao diện cùng backend tại `/frontend/`, hoặc mở `frontend/index.html` bằng VS Code Live Server cổng **5500**. Cách tương đương bằng Python, chạy ở terminal thứ hai tại thư mục gốc dự án:

```bash
python -m http.server 5500 --bind 127.0.0.1
```

Truy cập <http://127.0.0.1:5500/frontend/>. Khi frontend ở cổng 5500, JavaScript gọi API `http://127.0.0.1:8000/api/v1`; khi frontend được FastAPI phục vụ, JavaScript dùng `/api/v1` cùng origin. Link tài liệu cũng trỏ về backend. Nếu dùng địa chỉ API khác, đặt URL đầy đủ vào `content` của thẻ `<meta name="api-base">` trong `frontend/index.html`.

Backend cho phép hai origin mặc định `http://localhost:5500` và `http://127.0.0.1:5500`. Khi đổi host/port hoặc triển khai, cấu hình `.env` rồi khởi động lại backend:

```dotenv
CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,https://your-frontend.example.com
```

Origin là **scheme + host + port**, không có đường dẫn. CORS middleware cho phép preflight `OPTIONS`, JSON và header `Authorization`; không bật cookie credentials. CORS không thay thế đăng nhập hay phân quyền.

Để thực hành lỗi CORS trong Lab 2, tạm đặt `CORS_ORIGINS=` rồi restart backend: trình duyệt sẽ chặn frontend ở cổng 5500 đọc response; sau đó khôi phục giá trị trên và restart. `/docs` cùng origin và curl vẫn gọi được API trong lúc này.

Giao diện có bảng ID/tên/tuổi/team/power/status, form tạo hero tự tải lại bảng khi thành công và thông báo validation kèm tên trường (ví dụ `age: Input should be greater than or equal to 0`). Dropdown **Lọc theo biệt đội** lấy dữ liệu từ `GET /teams` và gọi `GET /teams/{id}/heroes`. Việc tạo/sửa/xóa vẫn cần đăng nhập theo Week 11; tạo team cần admin. Các trường có ràng buộc HTML cũng được trình duyệt kiểm tra trước khi gửi; test API kiểm tra riêng trường hợp gửi tuổi âm và các lỗi 422.

API dùng `HeroPublic` cho mọi response hero, ẩn `secret_name`, serialize `status` thành `active`/`retired` và `created_at` thành ISO 8601 có UTC. Client không tự đặt `created_at`. Pagination dùng `offset >= 0`, `1 <= limit <= 100`; lọc team không tồn tại trả `[]`, còn truy cập `/teams/{id}/heroes` của team không tồn tại trả `404`.

## Kiểm thử

```bash
source .venv/bin/activate
python -m pytest -v
```

Tests tự dùng khóa riêng và SQLite tạm/in-memory, không kết nối database của bạn. Bao gồm hash/salt, giới hạn 72 byte, JWT hợp lệ/bị sửa/sai khóa/hết hạn/thiếu claims, 401/403, owner/admin, URL cũ, validation/filter, OpenAPI, phục vụ frontend và migration giữ lại dữ liệu cũ. Các file `test_heroes.py`, `test_teams.py`, `test_cors.py` kiểm tra chi tiết hợp đồng REST của Week 10: 200/201/204/400/404/409/422, PATCH từng phần, timestamp UTC, origin được phép/bị từ chối và preflight có Bearer header. `pytest.ini` cấu hình `pythonpath = .` nên cũng có thể chạy `.venv/bin/pytest -v`.

## Ghi chú bảo mật theo bài học

- **Authentication** xác định danh tính; thiếu/sai/hết hạn token trả `401` kèm `WWW-Authenticate: Bearer`. **Authorization** kiểm tra quyền; tài khoản đúng nhưng không đủ quyền trả `403`.
- bcrypt là hash một chiều, có salt ngẫu nhiên cho từng mật khẩu; cùng mật khẩu tạo ra hash khác nhau. Hash khác mã hóa hai chiều. Chỉ lưu `hashed_password`, không trả password/hash qua API.
- JWT gồm `header.payload.signature`. Payload chỉ chứa `sub` và `exp`, ai cũng có thể giải mã Base64URL để đọc; chữ ký bảo vệ tính toàn vẹn. API chỉ chấp nhận HS256, bắt buộc `sub`/`exp`, tra lại user/role từ database.
- Client không quyết định `role` hoặc `owner_id`; hai trường này không có trong input schema tương ứng.
- Dùng HTTPS khi triển khai. Header Bearer không tự được trình duyệt gắn như cookie, giảm nguy cơ CSRF. Token trong sessionStorage vẫn có thể bị đọc nếu có XSS; vì vậy hiển thị dữ liệu bằng text, không bằng HTML.
- SQLModel dùng truy vấn tham số, không ghép input vào câu SQL. `SECRET_KEY` và thông tin kết nối database nằm trong biến môi trường/`.env`, không đưa vào Git. Thiếu `SECRET_KEY` khiến ứng dụng dừng lúc khởi động.
