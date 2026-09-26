"""Cấu trúc 278 nguyên lý / 22 nhóm."""

PRINCIPLE_GROUPS = {
    0:  {"name": "Khả năng điều phối", "count": 20, "items": [
        "Đọc toàn bộ đoạn chat", "Nhận biết việc đang làm dở", "Nhận biết user đổi chủ đề",
        "Phát hiện code, ảnh, số liệu, file", "Nhận biết ngôn ngữ và giọng điệu",
        "Phân loại yêu cầu vào nhóm chính", "Phân loại nhóm phụ", "Đánh giá độ rõ ràng",
        "Biết danh sách model user có", "Biết điểm mạnh, điểm yếu từng model",
        "Tra bảng nhóm yêu cầu -> nhóm model", "Chọn model phù hợp nhất",
        "Chuẩn bị fallback", "Chuyển model không mất ngữ cảnh",
        "Kể lại ngữ cảnh cho model mới", "Viết prompt tối ưu", "Thêm ràng buộc",
        "Kiểm tra kết quả", "Phát hiện output sai, gọi lại", "Giữ mạch cuộc chat",
    ]},
    1:  {"name": "Phép toán", "count": 10, "items": [
        "Cộng", "Trừ", "Nhân", "Chia", "Lũy thừa", "Căn", "Phần trăm", "Tỉ lệ",
        "Trung bình", "Thứ tự phép toán",
    ]},
    2:  {"name": "Nguyên lý chung", "count": 10, "items": [
        "Nguyên nhân - kết quả", "So sánh", "Phân loại", "Tổng quát hóa", "Đặc biệt hóa",
        "Tương tự", "Đối lập", "Nhân quả", "Điều kiện", "Mâu thuẫn",
    ]},
    3:  {"name": "Cách tạo code", "count": 16, "items": [
        "Biến", "Hàm", "Tham số", "Return", "Điều kiện rẽ nhánh", "Vòng lặp", "Mảng",
        "Object", "Class", "Kế thừa", "Hàm thuần khiết", "Tách hàm", "Đặt tên có nghĩa",
        "Comment", "Xử lý lỗi", "Nhập/xuất",
    ]},
    4:  {"name": "Tìm lỗi, sửa bug", "count": 15, "items": [
        "Đọc lỗi trước", "Tìm dòng lỗi", "Kiểm tra input", "Kiểm tra output",
        "So sánh mong đợi vs thực tế", "Chia để trị", "In debug", "Kiểm tra điều kiện biên",
        "Kiểm tra vòng lặp vô hạn", "Kiểm tra off-by-one", "Kiểm tra kiểu dữ liệu",
        "Kiểm tra null/None", "Kiểm tra logic", "Cô lập lỗi", "Tìm lỗi tương tự",
    ]},
    5:  {"name": "Sửa ảnh", "count": 15, "items": [
        "Ảnh là ma trận", "Pixel RGB", "Độ sáng", "Độ tương phản", "Lọc nhiễu", "Làm nét",
        "Đổi kích thước", "Cắt ảnh", "Xoay ảnh", "Đổi màu", "Tăng/giảm sáng", "Tách nền",
        "Xóa vật thể", "Thêm vật thể", "Phong cách hóa",
    ]},
    6:  {"name": "Viết văn", "count": 8, "items": [
        "Cấu trúc đoạn văn", "Ngôi kể", "Giọng điệu", "Từ nối câu", "Tránh lặp từ",
        "Câu chủ động vs bị động", "Độ dài câu", "Mục đích viết",
    ]},
    7:  {"name": "Dịch", "count": 6, "items": [
        "Dịch sát nghĩa", "Dịch thoát nghĩa", "Giữ văn phong", "Xử lý thành ngữ",
        "Xử lý từ chuyên ngành", "Ngữ cảnh văn hóa",
    ]},
    8:  {"name": "Phân tích dữ liệu", "count": 7, "items": [
        "Đọc bảng", "Tính tổng, trung bình, min, max", "Tìm xu hướng", "So sánh nhóm",
        "Tìm mối liên hệ", "Vẽ biểu đồ", "Rút insight",
    ]},
    9:  {"name": "Lập kế hoạch", "count": 6, "items": [
        "Xác định mục tiêu", "Chia bước", "Xác định thứ tự", "Xác định nguồn lực",
        "Xác định rủi ro", "Đặt mốc thời gian",
    ]},
    10: {"name": "Tra web", "count": 5, "items": [
        "Chọn từ khóa", "Đọc kết quả tìm kiếm", "Trích xuất thông tin",
        "Đánh giá độ tin cậy", "Tổng hợp từ nhiều nguồn",
    ]},
    11: {"name": "Kiến trúc phần mềm", "count": 20, "items": [
        "Kiến trúc là gì", "Tách module", "Tách layer", "MVC/MVP/MVVM",
        "Microservices vs Monolith", "API design", "GraphQL", "WebSocket", "Message queue",
        "Event-driven", "Cache strategy", "Load balancing", "Database design",
        "Normalization", "Index", "Transaction", "Replication", "Sharding",
        "CAP theorem", "Consistency models",
    ]},
    12: {"name": "Thuật toán nâng cao", "count": 20, "items": [
        "Big O", "Đệ quy", "Quy hoạch động", "Tham lam", "Chia để trị", "Quay lui",
        "Tìm kiếm nhị phân", "Sắp xếp", "BFS/DFS", "Dijkstra", "Bellman-Ford",
        "Floyd-Warshall", "Cây", "Heap", "Hash table", "Graph algorithms",
        "String matching", "Bit manipulation", "Randomized algorithms", "Approximation algorithms",
    ]},
    13: {"name": "Design patterns", "count": 15, "items": [
        "Singleton", "Factory", "Builder", "Adapter", "Decorator", "Observer", "Strategy",
        "Command", "Iterator", "Repository", "Dependency Injection", "MVC pattern",
        "CQRS", "Saga", "Circuit Breaker",
    ]},
    14: {"name": "Hệ thống lớn", "count": 15, "items": [
        "Scalability", "High availability", "Fault tolerance", "Disaster recovery",
        "Monitoring", "Logging tập trung", "Tracing", "Rate limiting", "Throttling",
        "Circuit breaker", "Retry strategy", "Idempotency", "Distributed lock",
        "Consensus", "Leader election",
    ]},
    15: {"name": "Bảo mật", "count": 15, "items": [
        "Authentication vs Authorization", "OAuth 2.0", "JWT", "Session vs Token",
        "HTTPS/TLS", "Mã hóa đối xứng", "Mã hóa bất đối xứng", "Hash function",
        "Salt & Pepper", "SQL Injection", "XSS", "CSRF", "CORS",
        "Rate limiting bảo mật", "Zero trust",
    ]},
    16: {"name": "Tối ưu hiệu năng", "count": 15, "items": [
        "Profiling", "Benchmarking", "Memory optimization", "CPU optimization",
        "I/O optimization", "Lazy loading", "Eager loading", "Caching", "CDN",
        "Compression", "Minification", "Bundle splitting", "Code splitting",
        "Database query optimization", "Index optimization",
    ]},
    17: {"name": "Sáng tạo", "count": 10, "items": [
        "Brainstorming", "Mind mapping", "SCAMPER", "Six Thinking Hats",
        "First principles thinking", "Analogical thinking", "Reverse thinking",
        "Lateral thinking", "Combinatorial creativity", "Constraint-based creativity",
    ]},
    18: {"name": "Chiến lược & ra quyết định", "count": 15, "items": [
        "SWOT", "PEST", "Porter's 5 Forces", "Cost-benefit analysis", "Decision tree",
        "Expected value", "Opportunity cost", "Risk assessment", "Trade-off analysis",
        "Prioritization", "OKR", "KPI", "Roadmap", "Scenario planning", "Game theory",
    ]},
    19: {"name": "Giao tiếp nâng cao", "count": 10, "items": [
        "Thuyết phục", "Đàm phán", "Kể chuyện", "Thuyết trình", "Viết tài liệu kỹ thuật",
        "Viết proposal", "Phản hồi", "Xử lý xung đột", "Đặt câu hỏi", "Lắng nghe chủ động",
    ]},
    20: {"name": "Tư duy hệ thống", "count": 10, "items": [
        "Systems thinking", "Feedback loops", "Emergence", "Leverage points",
        "Bottleneck analysis", "Root cause analysis", "Fishbone diagram",
        "Pareto principle", "Second-order thinking", "Inversion",
    ]},
    21: {"name": "Kiến thức liên ngành", "count": 15, "items": [
        "Tâm lý học", "Kinh tế học", "Triết học", "Lịch sử công nghệ", "Đạo đức AI",
        "Luật cơ bản", "Y tế cơ bản", "Tài chính cá nhân", "Marketing",
        "Quản lý dự án", "Agile/Scrum", "DevOps", "Testing", "CI/CD", "Version control",
    ]},
}


def total_principles() -> int:
    return sum(g["count"] for g in PRINCIPLE_GROUPS.values())


def get_all_titles():
    """Trả về list (group_id, title) cho toàn bộ 278 nguyên lý."""
    out = []
    for gid, g in PRINCIPLE_GROUPS.items():
        for title in g["items"]:
            out.append((gid, title))
    return out