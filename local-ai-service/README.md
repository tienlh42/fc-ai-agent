# Local AI API Service MVP

REST API chạy trên Windows, dùng Qwen qua Ollama và LlamaIndex. Service có
tool registry cố định, validation bằng JSON Schema và vòng function-calling có
giới hạn. MVP không có RAG, vector database, streaming hay lưu lịch sử.

Model Django của nghiệp vụ feedback được lưu tại
`docs/reference/feedback_models.py` để làm nguồn tham chiếu khi tạo hoặc cập
nhật JSON Schema cho feedback tool. File này không được import vào runtime.

## Cấu trúc

```text
local-ai-service/
├── app/
│   ├── api/                 # FastAPI routes và schemas
│   ├── ai/                  # Ollama, parser và function-calling loop
│   ├── clients/             # External REST API client
│   ├── core/                # Exceptions
│   ├── tools/               # Registry, schemas, handlers, executor
│   ├── config.py
│   ├── dependencies.py
│   └── main.py
├── tests/
├── .env.example
├── requirements.txt
└── run.ps1
```

## Chuẩn bị

Yêu cầu Python 3.11+ và [Ollama](https://ollama.com/) đã được cài:

```powershell
ollama pull qwen3:8b
ollama list
curl.exe http://127.0.0.1:11434/api/tags
```

Tạo môi trường Python:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Sửa `.env`, đặt `EXTERNAL_API_BASE_URL` và `EXTERNAL_API_KEY` thật. API key chỉ
được tự động gắn vào header do HTTP client quản lý; không được đưa vào prompt,
tham số tool, URL hay log.

## Chạy

Chạy toàn bộ API và Ollama bằng Docker Compose (lần đầu sẽ tự tải model):

```powershell
Copy-Item .env.example .env
# Cập nhật EXTERNAL_API_BASE_URL và EXTERNAL_API_KEY trong .env
docker compose up --build -d
docker compose logs -f ollama-pull local-ai-service
```

Model được lưu trong volume `ollama-data`. API gọi Ollama bằng địa chỉ nội bộ
`http://ollama:11434` và được truy cập từ máy host tại
`http://127.0.0.1:8010`. Khi backend chạy trên máy host, Compose sử dụng
`DOCKER_EXTERNAL_API_BASE_URL=http://host.docker.internal:8080/`; biến
`EXTERNAL_API_BASE_URL` vẫn dành cho trường hợp chạy service trực tiếp. Thư mục
`app/` được bind-mount vào container và Uvicorn chạy với `--reload`, nên thay đổi
source code trên máy host được tự động nạp lại mà không cần build image.

Chạy trực tiếp từ Windows Terminal:

```powershell
.\start.cmd
```

Hoặc chạy PowerShell script:

```powershell
.\run.ps1
```

## Test model trực tiếp

Mở phiên chat tương tác trực tiếp với model qua Ollama, không cần chạy API và
không cần `curl`:

```powershell
.\test-model.cmd
```

Hoặc hỏi một câu rồi thoát:

```powershell
.\test-model.cmd "Xin chào, hãy giới thiệu ngắn gọn về bạn"
```

Script đọc model từ `OLLAMA_MODEL` trong `.env`; nếu chưa có `.env` thì dùng
`qwen3:8b`.

Health check:

```powershell
curl.exe http://127.0.0.1:8010/health
```

Chat:

```powershell
curl.exe -X POST http://127.0.0.1:8010/api/v1/chat `
  -H "Content-Type: application/json" `
  -d '{"message":"Tìm học sinh Nguyễn Văn An"}'
```

Response mẫu:

```json
{
  "success": true,
  "answer": "Tôi tìm thấy học sinh Nguyễn Văn An.",
  "tool_calls": [
    {
      "name": "search_students",
      "arguments": {"search": "Nguyễn Văn An", "limit": 10},
      "success": true
    }
  ]
}
```

Chạy unit tests (không cần Ollama hoặc external backend thật):

```powershell
pytest -q
```

## Function-calling loop

Model nhận system prompt cùng allow-list schema của bốn tool. Mỗi lượt model chỉ
được trả JSON `tool_call` hoặc `final_answer`. Với `tool_call`, service kiểm tra
tên, validate arguments, chạy handler rồi thêm kết quả vào context cho lượt kế
tiếp. Loop dừng khi có câu trả lời cuối, đạt `MAX_TOOL_ROUNDS`, hoặc cùng tool và
arguments bị yêu cầu lần thứ ba.

Các endpoint external được cố định trong handler:

- `search_students`: `GET /api/students`
- `get_student_detail`: `GET /api/students/{student_number}`
- `create_feedback_ticket`: `POST /api/feedback/tickets`
- `get_feedback_list`: `GET /feedback/api/feedback/list`, hỗ trợ lọc theo
  `title`, `description`, `priority` (`low`, `medium`, `high`), `reason_id`,
  `guardian_id`, `student_id`, `campus_id`, `feedback_status` (`new`, `review`,
  `processing`, `verified`, `close-ticket`) và `source`. Tất cả bộ lọc đều
  không bắt buộc.

## Lỗi thường gặp

- `OLLAMA_UNAVAILABLE`: Ollama chưa chạy, model chưa được pull, sai
  `OLLAMA_BASE_URL`, hoặc request hết timeout. Kiểm tra `/api/tags` và `ollama list`.
- Health trả `degraded`: Ollama không phản hồi; cấu hình external API không được
  gọi thật trong health check.
- External API trả 401/403: kiểm tra key và tên header `Api-Key`.
- External API trả 404: xác minh backend thực tế hỗ trợ đúng bốn endpoint cố định.
- Timeout external API: backend chưa chạy, sai host/port hoặc tăng
  `EXTERNAL_API_TIMEOUT` nếu backend phản hồi chậm.
- Model response parse error: model không tuân thủ JSON; giữ temperature thấp và
  đảm bảo đang dùng model Qwen có khả năng làm theo structured prompt.
