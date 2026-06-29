# Đồ Án Lab Day 08 — LangGraph Support Ticket Agent

Dự án này là một hệ thống Agent hỗ trợ khách hàng được xây dựng bằng **LangGraph**. Hệ thống được thiết kế chuẩn Production với các tính năng như state management (quản lý trạng thái), conditional routing (điều hướng có điều kiện), retry loops (vòng lặp thử lại), Human-in-the-Loop (người duyệt), persistence (lưu trữ), và đánh giá metrics tự động.

---

## 🌟 Các tính năng nổi bật (Đã hoàn thành)

1. **Phân loại ý định bằng LLM**: Kịch bản `classify_node` sử dụng LLM với Structured Output để tự động phân luồng yêu cầu của khách hàng (simple, missing_info, tool, error, risky).
2. **Cơ chế Human-in-the-Loop (HITL) thực sự**: Các hành động rủi ro cao (hoàn tiền, xoá dữ liệu) sẽ làm hệ thống tạm dừng (Suspend) thông qua `interrupt()` của LangGraph và chờ người quản trị phê duyệt.
3. **LLM-as-judge**: Sử dụng một LLM độc lập để đánh giá kết quả từ công cụ trả về, tự động quyết định xem có cần chạy lại vòng lặp (Retry) hay không.
4. **Quản lý trạng thái & Persistence**: Tích hợp `SqliteSaver` trong chế độ WAL cho phép lưu trữ và khôi phục trạng thái bất kỳ lúc nào, quản lý hội thoại theo từng `thread_id` độc lập.
5. **Giao diện Web tương tác (Streamlit)**: Có sẵn một giao diện UI hiện đại để chat với Agent và có các nút bấm tương tác (Approve/Reject) thay vì chỉ chạy code trên Terminal.
6. **Báo cáo và Testing**: Hệ thống đi qua 100% tất cả 7 kịch bản chấm điểm cực kỳ khắt khe của bộ Test `run-scenarios`.

---

## 🚀 Hướng dẫn cài đặt và sử dụng

### 1. Cài đặt môi trường
Bạn nên sử dụng Conda hoặc Venv để tạo môi trường (yêu cầu Python >= 3.11):
```bash
conda create -n day8-lab python=3.11 -y
conda activate day8-lab

# Cài đặt các thư viện cần thiết
pip install -e '.[dev]'
pip install langchain-openai python-dotenv langgraph-checkpoint-sqlite
```

### 2. Cấu hình API Key
Mở file `.env` (hoặc copy từ `.env.example`) và điền API Key của bạn:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxxxxxxxxxxxxxxxxxxx
LANGCHAIN_PROJECT=day8-langgraph-agent-lab
LANGGRAPH_INTERRUPT=false
CHECKPOINTER=sqlite
LOG_LEVEL=INFO
```
*(Ghi chú: Để chế độ `LANGGRAPH_INTERRUPT=false` khi bạn muốn tự động chạy bộ test, và `true` khi muốn tự test HITL)*

### 3. Khởi chạy Giao diện Streamlit
Để thử nghiệm bot hỗ trợ và trải nghiệm luồng chờ phê duyệt của con người, hãy chạy:
```bash
streamlit run app.py
```
Hãy thử chat câu: *"Refund this customer"* để xem hệ thống phát hiện rủi ro và tạm dừng như thế nào!

### 4. Chạy bộ kiểm thử tự động (Scenarios / Testing)
```bash
# Chạy bộ unit tests
pytest tests/

# Chạy chấm điểm 7 kịch bản tự động
python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json

# Xác nhận kết quả
python -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
```
Kết quả chấm điểm và báo cáo tự động (bằng tiếng Việt) sẽ được sinh ra ở file `reports/lab_report.md`.

---

## 🛠 Lược đồ thiết kế

- **classify_node**: Phân loại yêu cầu.
- **tool_node**: Thực thi công cụ (mock).
- **evaluate_node**: LLM-as-judge nhận xét kết quả.
- **answer_node**: Sinh ra câu trả lời dựa trên thông tin đã tổng hợp.
- **risky_action_node & approval_node**: Xử lý các tác vụ nhạy cảm cần xác nhận.
- **retry_or_fallback_node & dead_letter_node**: Quản lý rủi ro và các lỗi gián đoạn từ hệ thống công cụ.

## 👥 Tác giả
Sinh viên: **Nguyễn Thành Đạt - 2A202600771**
Hoàn thành với số điểm 100% trong bộ test kịch bản tự động.
