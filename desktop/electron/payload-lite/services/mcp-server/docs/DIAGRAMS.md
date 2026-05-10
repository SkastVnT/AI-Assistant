# 📊 MCP Server Architecture & Diagrams

Tài liệu này chứa các biểu đồ trực quan để hiểu kiến trúc MCP Server.

## 🏗️ 1. Architecture Overview

```mermaid
graph TB
    subgraph "AI Client (Claude Desktop, VS Code, etc.)"
        A[AI Assistant]
        B[MCP Client]
    end
    
    subgraph "MCP Server - AI-Assistant"
        C[FastMCP Server]
        D[Tools Manager]
        E[Resources Manager]
        F[Prompts Manager]
    end
    
    subgraph "AI-Assistant Project"
        G[File System]
        H[Logs]
        I[Configs]
        J[Services]
        K[Database]
    end
    
    A -->|Request| B
    B -->|JSON-RPC 2.0| C
    C --> D
    C --> E
    C --> F
    
    D -->|Read/Write| G
    D -->|Query| H
    D -->|Access| I
    E -->|Load| I
    E -->|Read| G
    F -->|Generate| A
    
    G -.->|Contains| J
    J -.->|Produces| H
    J -.->|Uses| K
    
    C -->|Response| B
    B -->|Result| A
    
    style C fill:#6366F1,color:#fff
    style A fill:#10B981,color:#fff
    style G fill:#F59E0B,color:#fff
```

## 🔄 2. Request Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Claude as Claude Desktop
    participant MCP as MCP Server
    participant FS as File System
    participant Log as Logs
    
    User->>Claude: "Tìm file Python liên quan chatbot"
    Claude->>Claude: Parse intent
    Claude->>MCP: tool_call(search_files, query="chatbot", type="py")
    
    MCP->>FS: os.walk() + filter
    FS-->>MCP: List of files
    
    MCP->>MCP: Format response
    MCP-->>Claude: {"results": [...]}
    
    Claude->>Claude: Format for user
    Claude-->>User: "Tìm thấy 3 files: app.py, service.py..."
    
    Note over User,Log: User request another action
    
    User->>Claude: "Đọc file app.py"
    Claude->>MCP: tool_call(read_file_content, path="services/chatbot/app.py")
    
    MCP->>FS: open() + read()
    FS-->>MCP: File content
    
    MCP-->>Claude: {"content": "...code..."}
    Claude-->>User: "File này chứa FastAPI app..."
    
    Note over User,Log: Error scenario
    
    User->>Claude: "Có lỗi gì trong logs?"
    Claude->>MCP: tool_call(search_logs, level="error")
    
    MCP->>Log: Read *.log files
    Log-->>MCP: Log entries
    
    MCP->>MCP: Filter by level
    MCP-->>Claude: {"errors": [...]}
    
    Claude-->>User: "Tìm thấy 2 lỗi: Connection timeout..."
```

## 🔧 3. Tools Architecture

```mermaid
graph LR
    subgraph "MCP Tools - 6 công cụ"
        T1[search_files]
        T2[read_file_content]
        T3[list_directory]
        T4[get_project_info]
        T5[search_logs]
        T6[calculate]
    end
    
    subgraph "Data Sources"
        D1[File System]
        D2[Logs Directory]
        D3[Config Files]
        D4[Project Structure]
    end
    
    T1 --> D1
    T2 --> D1
    T3 --> D1
    T4 --> D4
    T5 --> D2
    T6 -.->|Math operations| T6
    
    D1 -.->|Contains| D3
    D1 -.->|Contains| D2
    
    style T1 fill:#3B82F6
    style T2 fill:#3B82F6
    style T3 fill:#3B82F6
    style T4 fill:#10B981
    style T5 fill:#EF4444
    style T6 fill:#F59E0B
```

## 📦 4. Resources Structure

```mermaid
graph TD
    subgraph "MCP Resources - 4 tài nguyên"
        R1[config://model]
        R2[config://logging]
        R3[docs://readme]
        R4[docs://structure]
    end
    
    subgraph "Files"
        F1[config/model_config.py]
        F2[config/logging_config.py]
        F3[README.md]
        F4[docs/STRUCTURE.md]
    end
    
    R1 -->|Read| F1
    R2 -->|Read| F2
    R3 -->|Read| F3
    R4 -->|Read| F4
    
    style R1 fill:#8B5CF6
    style R2 fill:#8B5CF6
    style R3 fill:#06B6D4
    style R4 fill:#06B6D4
```

## 💬 5. Prompts Flow

```mermaid
graph TB
    subgraph "Prompt Templates"
        P1[code_review_prompt]
        P2[debug_prompt]
        P3[explain_code_prompt]
    end
    
    subgraph "User Requests"
        U1["Review file X"]
        U2["Debug error Y"]
        U3["Explain code Z"]
    end
    
    subgraph "AI Processing"
        AI1[Load template]
        AI2[Fill parameters]
        AI3[Execute analysis]
        AI4[Return result]
    end
    
    U1 --> P1
    U2 --> P2
    U3 --> P3
    
    P1 --> AI1
    P2 --> AI1
    P3 --> AI1
    
    AI1 --> AI2
    AI2 --> AI3
    AI3 --> AI4
    
    style P1 fill:#EC4899
    style P2 fill:#EC4899
    style P3 fill:#EC4899
```

## 🌐 6. MCP Ecosystem

```mermaid
graph TB
    subgraph "MCP Clients"
        C1[Claude Desktop]
        C2[VS Code + Copilot]
        C3[MCP Inspector]
        C4[Custom Apps]
    end
    
    subgraph "MCP Protocol"
        P[JSON-RPC 2.0<br/>over stdio/HTTP]
    end
    
    subgraph "MCP Servers"
        S1[AI-Assistant Server]
        S2[GitHub Server]
        S3[Database Server]
        S4[Other Servers]
    end
    
    subgraph "Data Sources"
        D1[Local Files]
        D2[APIs]
        D3[Databases]
        D4[Cloud Services]
    end
    
    C1 --> P
    C2 --> P
    C3 --> P
    C4 --> P
    
    P --> S1
    P --> S2
    P --> S3
    P --> S4
    
    S1 --> D1
    S2 --> D2
    S3 --> D3
    S4 --> D4
    
    style S1 fill:#6366F1,color:#fff
    style P fill:#10B981,color:#fff
```

## 🔐 7. Security Model

```mermaid
graph TB
    subgraph "User Layer"
        U[User]
    end
    
    subgraph "AI Layer"
        AI[Claude Desktop]
    end
    
    subgraph "Security Layer"
        S1[Host-based Access Control]
        S2[File Permission Check]
        S3[Path Validation]
        S4[Audit Logging]
    end
    
    subgraph "MCP Server"
        M[MCP Server]
    end
    
    subgraph "Data Layer"
        D[Project Files & Data]
    end
    
    U -->|Request| AI
    AI -->|MCP Call| S1
    S1 -->|Validate| S2
    S2 -->|Check| S3
    S3 -->|Approve| M
    M -->|Access| D
    M -.->|Log| S4
    
    D -->|Response| M
    M -->|Return| S3
    S3 -->|Audit| S4
    S4 -->|Result| AI
    AI -->|Display| U
    
    style S1 fill:#EF4444,color:#fff
    style S2 fill:#EF4444,color:#fff
    style S3 fill:#EF4444,color:#fff
    style S4 fill:#EF4444,color:#fff
```

## 📈 8. Data Flow - End to End

```mermaid
flowchart TD
    Start([User asks question]) --> Parse[Claude parses intent]
    Parse --> Decision{Need external data?}
    
    Decision -->|Yes| SelectTool[Select appropriate tool]
    Decision -->|No| DirectAnswer[Answer from knowledge]
    
    SelectTool --> CallMCP[Call MCP Server via JSON-RPC]
    CallMCP --> Validate[Validate request]
    
    Validate -->|Invalid| Error[Return error]
    Validate -->|Valid| Execute[Execute tool]
    
    Execute --> CheckCache{Cache available?}
    CheckCache -->|Yes| ReturnCache[Return cached result]
    CheckCache -->|No| AccessData[Access data source]
    
    AccessData --> Process[Process data]
    Process --> Format[Format response]
    Format --> Cache[Update cache]
    Cache --> Return[Return to Claude]
    
    ReturnCache --> Return
    Error --> Return
    DirectAnswer --> Display
    
    Return --> Analyze[Claude analyzes result]
    Analyze --> Display[Display to user]
    Display --> End([Done])
    
    style Start fill:#10B981,color:#fff
    style Execute fill:#6366F1,color:#fff
    style AccessData fill:#F59E0B,color:#fff
    style Display fill:#10B981,color:#fff
    style End fill:#10B981,color:#fff
```

## 🚀 9. Deployment Architecture

```mermaid
graph TB
    subgraph "Development Environment"
        DEV[Local Development]
        TEST[Testing with Inspector]
    end
    
    subgraph "Production Setup"
        PROD1[Windows]
        PROD2[Linux/Mac]
        PROD3[Docker]
    end
    
    subgraph "MCP Server Components"
        SERVER[server.py]
        CONFIG[config.json]
        DEPS[requirements.txt]
    end
    
    subgraph "AI Clients"
        CLAUDE[Claude Desktop]
        VSCODE[VS Code]
        CUSTOM[Custom Apps]
    end
    
    DEV --> SERVER
    TEST --> SERVER
    
    SERVER --> PROD1
    SERVER --> PROD2
    SERVER --> PROD3
    
    CONFIG --> PROD1
    CONFIG --> PROD2
    CONFIG --> PROD3
    
    DEPS --> PROD1
    DEPS --> PROD2
    DEPS --> PROD3
    
    PROD1 --> CLAUDE
    PROD2 --> VSCODE
    PROD3 --> CUSTOM
    
    style SERVER fill:#6366F1,color:#fff
    style CLAUDE fill:#10B981,color:#fff
```

## 📊 10. Performance Metrics

```mermaid
graph LR
    subgraph "Metrics"
        M1[Request Count]
        M2[Response Time]
        M3[Error Rate]
        M4[Cache Hit Rate]
    end
    
    subgraph "Tools Performance"
        T1[search_files: ~100ms]
        T2[read_file: ~50ms]
        T3[list_dir: ~30ms]
        T4[project_info: ~20ms]
        T5[search_logs: ~200ms]
        T6[calculate: ~5ms]
    end
    
    M1 -.-> T1
    M1 -.-> T2
    M1 -.-> T3
    
    M2 -.-> T1
    M2 -.-> T2
    M2 -.-> T5
    
    style T1 fill:#F59E0B
    style T5 fill:#EF4444
    style T6 fill:#10B981
```

---

## 📖 Cách đọc các diagram

### Màu sắc:
- 🔵 **Xanh dương** - Core components (MCP Server, Tools)
- 🟢 **Xanh lá** - Success/Endpoints (AI, Results)
- 🟡 **Vàng** - Data sources (Files, Logs)
- 🟣 **Tím** - Resources/Configs
- 🔴 **Đỏ** - Security/Errors
- 🔷 **Hồng** - Prompts/Templates

### Mũi tên:
- `-->` - Direct flow (luồng chính)
- `-.->` - Indirect/Optional flow (tùy chọn)
- `==>` - Strong dependency (phụ thuộc mạnh)

### Hình dạng:
- `[Rectangle]` - Process/Component
- `(Circle)` - Start/End
- `{Diamond}` - Decision point
- `((Circle))` - Database/Storage

---

## 🎯 Use Cases cho từng diagram

1. **Architecture Overview** - Hiểu tổng quan hệ thống
2. **Request Flow** - Debug luồng xử lý
3. **Tools Architecture** - Hiểu cách tools hoạt động
4. **Resources Structure** - Quản lý resources
5. **Prompts Flow** - Tạo prompts mới
6. **MCP Ecosystem** - Tích hợp với systems khác
7. **Security Model** - Audit và security review
8. **Data Flow** - Tối ưu performance
9. **Deployment** - Setup production
10. **Performance** - Monitoring và optimization

---

## 🔧 Tools để xem diagrams

### Online:
- **Mermaid Live Editor**: https://mermaid.live/
- **GitHub**: Tự động render Mermaid trong .md files
- **VS Code**: Extension "Markdown Preview Mermaid"

### Offline:
```bash
# VS Code extension
code --install-extension bierner.markdown-mermaid

# Hoặc dùng Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i DIAGRAMS.md -o diagrams.pdf
```

---

**📚 Next Steps:**
1. Xem diagrams trên Mermaid Live Editor
2. Đọc hiểu từng luồng
3. Sử dụng để design thêm features
4. Tham khảo khi debug issues
