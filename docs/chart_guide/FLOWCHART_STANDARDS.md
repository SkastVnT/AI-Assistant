# 📊 Flowchart Drawing Standards & Guidelines

> **Comprehensive guide for creating professional flowcharts**  
> **Version:** 1.0.0  
> **Updated:** November 6, 2025

---

## 📋 Table of Contents

1. [Introduction](#-introduction)
2. [Basic Flowchart Symbols](#-basic-flowchart-symbols)
3. [Design Principles](#-design-principles)
4. [Naming Conventions](#-naming-conventions)
5. [Layout Guidelines](#-layout-guidelines)
6. [Mermaid Syntax Guide](#-mermaid-syntax-guide)
7. [Best Practices](#-best-practices)
8. [Common Patterns](#-common-patterns)
9. [Anti-Patterns (What to Avoid)](#-anti-patterns-what-to-avoid)
10. [Tools & Resources](#-tools--resources)

---

## 🎯 Introduction

### Purpose

Flowcharts are visual representations of processes, workflows, and algorithms. This guide establishes standards for creating clear, consistent, and professional flowcharts in the AI-Assistant project.

### When to Use Flowcharts

- ✅ **Process Documentation** - Business workflows, approval processes
- ✅ **Algorithm Design** - Decision trees, logical flows
- ✅ **System Architecture** - Data flow, component interactions
- ✅ **Troubleshooting** - Debugging paths, error handling
- ✅ **Onboarding** - User journeys, feature walkthroughs

### When NOT to Use Flowcharts

- ❌ **Simple Linear Processes** - Use bullet lists instead
- ❌ **Complex Data Structures** - Use ER diagrams or class diagrams
- ❌ **Time-based Sequences** - Use sequence diagrams
- ❌ **Organizational Structure** - Use org charts

---

## 🔷 Basic Flowchart Symbols

### Standard Shapes & Their Meanings

| Shape | Symbol | Purpose | Usage |
|-------|--------|---------|-------|
| **Terminal** | ![Oval](https://via.placeholder.com/60x30/4CAF50/FFFFFF?text=Start) | Start/End points | Begin/terminate process |
| **Process** | ![Rectangle](https://via.placeholder.com/60x30/2196F3/FFFFFF?text=Action) | Operations/Actions | Any processing step |
| **Decision** | ![Diamond](https://via.placeholder.com/60x30/FFC107/000000?text=?) | Conditional branches | Yes/No, True/False |
| **Input/Output** | ![Parallelogram](https://via.placeholder.com/60x30/9C27B0/FFFFFF?text=I/O) | Data I/O | User input, file read/write |
| **Subprocess** | ![Rectangle with borders](https://via.placeholder.com/60x30/00BCD4/FFFFFF?text=Sub) | Predefined process | Call to another flowchart |
| **Document** | ![Wavy bottom](https://via.placeholder.com/60x30/FF5722/FFFFFF?text=Doc) | Document/Report | Generate report, print |
| **Database** | ![Cylinder](https://via.placeholder.com/60x30/795548/FFFFFF?text=DB) | Database operation | Query, insert, update |
| **Connector** | ![Circle](https://via.placeholder.com/30x30/607D8B/FFFFFF?text=A) | On-page connector | Link separated flows |
| **Off-page** | ![Pentagon](https://via.placeholder.com/60x30/FF9800/FFFFFF?text=1) | Off-page connector | Continue on another page |

### Arrows & Flow Lines

```
→   Normal flow (left to right)
↓   Sequential flow (top to bottom)
⤴   Return/Loop back
--→ Dotted line (optional or error path)
==→ Bold line (primary path)
```

---

## 🎨 Design Principles

### 1. **Clarity Over Complexity**

**Good:**
```
Start → Process → Decision → End
```

**Bad:**
```
Start → Process1 → Process2 → Process3 → SubProcess1 → SubProcess2 → Decision1 → Decision2 → Decision3 → ...
```

**Rule:** If flowchart has more than 15 nodes, split into multiple diagrams.

---

### 2. **Consistent Flow Direction**

**Top to Bottom (Preferred):**
```mermaid
flowchart TD
    A[Start] --> B[Process]
    B --> C[Decision]
    C -->|Yes| D[Action]
    C -->|No| E[End]
    D --> E
```

**Left to Right (Alternative):**
```mermaid
flowchart LR
    A[Start] --> B[Process] --> C[Decision]
    C -->|Yes| D[Action]
    C -->|No| E[End]
    D --> E
```

**Rule:** Choose ONE direction per diagram. Don't mix.

---

### 3. **Decision Nodes Always Binary**

**Good:**
```mermaid
flowchart TD
    A[Check User Role]
    A -->|Admin| B[Admin Dashboard]
    A -->|User| C[User Dashboard]
```

**Bad:**
```mermaid
flowchart TD
    A[Check User Role]
    A -->|Admin| B[Dashboard1]
    A -->|User| C[Dashboard2]
    A -->|Guest| D[Dashboard3]
    A -->|Moderator| E[Dashboard4]
```

**Rule:** Use multiple decision nodes for multi-way branching.

**Better:**
```mermaid
flowchart TD
    A[Check User Role]
    A -->|Admin?| B{Yes}
    A -->|No| C{Is User?}
    B --> D[Admin Dashboard]
    C -->|Yes| E[User Dashboard]
    C -->|No| F{Is Guest?}
    F -->|Yes| G[Guest View]
    F -->|No| H[Moderator Dashboard]
```

---

### 4. **Labels Must Be Actionable**

**Good:**
```
✅ "Validate Input"
✅ "Send Email Notification"
✅ "Calculate Total Price"
✅ "Query Database"
```

**Bad:**
```
❌ "Validation"
❌ "Email"
❌ "Price"
❌ "Database"
```

**Rule:** Use **Verb + Noun** format for action nodes.

---

### 5. **Color Coding (Optional but Recommended)**

```mermaid
flowchart TD
    classDef startEnd fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef process fill:#2196F3,stroke:#1565C0,color:#fff
    classDef decision fill:#FFC107,stroke:#F57F17,color:#000
    classDef error fill:#F44336,stroke:#C62828,color:#fff
    classDef database fill:#9C27B0,stroke:#6A1B9A,color:#fff
    
    A[Start]:::startEnd
    B[Process Data]:::process
    C{Valid?}:::decision
    D[Save to DB]:::database
    E[Error Handling]:::error
    F[End]:::startEnd
    
    A --> B --> C
    C -->|Yes| D --> F
    C -->|No| E --> F
```

**Color Scheme:**
- 🟢 **Green** - Start/End
- 🔵 **Blue** - Process/Action
- 🟡 **Yellow** - Decision
- 🔴 **Red** - Error/Exception
- 🟣 **Purple** - Database/Storage
- 🟠 **Orange** - External API/Service

---

## 📝 Naming Conventions

### Node Labels

#### **Start/End Nodes**
```
✅ Start
✅ End
✅ Begin Process
✅ Terminate Workflow

❌ S, E
❌ Start Here!!!
❌ The Beginning
```

#### **Process Nodes**
```
Format: [Verb] + [Object] + [Context (optional)]

✅ Validate User Input
✅ Calculate Invoice Total
✅ Send Confirmation Email
✅ Update Database Record
✅ Generate PDF Report

❌ Validating...
❌ Calculation
❌ Email
```

#### **Decision Nodes**
```
Format: Question ending with "?"

✅ Is User Authenticated?
✅ Payment Successful?
✅ Age > 18?
✅ Has Permission?

❌ User Auth
❌ Check Payment
❌ Age Check
```

#### **Decision Branches**
```
✅ Yes/No
✅ True/False
✅ Success/Failure
✅ Valid/Invalid
✅ Found/Not Found

❌ Y/N
❌ 1/0
❌ OK/Error
```

---

## 📐 Layout Guidelines

### Spacing & Alignment

```
Minimum spacing between nodes: 20px
Vertical spacing: 40px
Horizontal spacing: 60px

Grid alignment: Snap to 10px grid
```

### Maximum Complexity per Diagram

| Element | Maximum | Recommendation |
|---------|---------|----------------|
| Total Nodes | 20 | 10-15 |
| Decision Nodes | 5 | 3-4 |
| Nesting Levels | 4 | 2-3 |
| Branches per Decision | 2 | Always 2 |
| Connectors | 30 | 20 |

**If exceeding limits:** Split into multiple diagrams with subprocesses.

---

### Swimlanes (for Multi-Actor Processes)

```mermaid
flowchart TD
    subgraph User
        A[Submit Form]
        B[Receive Notification]
    end
    
    subgraph Backend
        C[Validate Data]
        D[Process Request]
        E[Send Email]
    end
    
    subgraph Database
        F[Save Record]
        G[Update Status]
    end
    
    A --> C
    C --> D
    D --> F
    F --> G
    G --> E
    E --> B
```

**Use swimlanes when:**
- Process involves multiple departments/actors
- Showing responsibility boundaries
- Illustrating system interactions

---

## 🛠️ Mermaid Syntax Guide

### Basic Flowchart Structure

```mermaid
flowchart TD
    Start[Start Process]
    Process[Do Something]
    Decision{Check Condition?}
    End[End Process]
    
    Start --> Process
    Process --> Decision
    Decision -->|Yes| End
    Decision -->|No| Process
```

**Code:**
```markdown
```mermaid
flowchart TD
    Start[Start Process]
    Process[Do Something]
    Decision{Check Condition?}
    End[End Process]
    
    Start --> Process
    Process --> Decision
    Decision -->|Yes| End
    Decision -->|No| Process
\```
```

---

### Node Shapes

```mermaid
flowchart LR
    A[Rectangle - Process]
    B([Rounded - Terminal])
    C{Diamond - Decision}
    D[(Database)]
    E[[Subroutine]]
    F[/Parallelogram - Input/]
    G[\Parallelogram - Output\]
    H((Circle - Connector))
```

**Syntax:**
```markdown
[Text]          Rectangle
([Text])        Rounded rectangle
{Text}          Diamond
[(Text)]        Database
[[Text]]        Subroutine
[/Text/]        Input (parallelogram)
[\Text\]        Output (parallelogram)
((Text))        Circle
```

---

### Arrow Types

```mermaid
flowchart LR
    A -->|Normal| B
    B -.->|Dotted| C
    C ==>|Bold| D
    D ---|No arrow| E
    E -->|Multi<br/>Line| F
```

**Syntax:**
```markdown
A --> B          Normal arrow
A -.-> B         Dotted arrow
A ==> B          Bold arrow
A --- B          Line without arrow
A -->|Label| B   Arrow with label
A -->|Line1<br/>Line2| B   Multi-line label
```

---

### Styling & Colors

```mermaid
flowchart TD
    A[Node 1]
    B[Node 2]
    C[Node 3]
    
    A --> B --> C
    
    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
```

**Syntax:**
```markdown
style NodeID fill:#color,stroke:#color,stroke-width:Xpx
```

---

### Using Classes (Reusable Styles)

```mermaid
flowchart TD
    classDef success fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef error fill:#F44336,stroke:#C62828,color:#fff
    classDef warning fill:#FFC107,stroke:#F57F17,color:#000
    
    A[Success Case]:::success
    B[Error Case]:::error
    C[Warning Case]:::warning
```

**Syntax:**
```markdown
classDef className fill:#color,stroke:#color,color:#color
NodeID:::className
```

---

### Subgraphs (Grouping)

```mermaid
flowchart TD
    subgraph Frontend
        A[UI Component]
        B[State Management]
    end
    
    subgraph Backend
        C[API Endpoint]
        D[Business Logic]
    end
    
    subgraph Database
        E[Query]
        F[Result]
    end
    
    A --> C
    C --> D
    D --> E
    E --> F
    F --> C
    C --> A
```

**Syntax:**
```markdown
subgraph GroupName
    Node1
    Node2
end
```

---

## ✅ Best Practices

### 1. **Start with Pen & Paper**

Before coding Mermaid, sketch the flow manually:
```
1. List all steps
2. Identify decision points
3. Mark start/end
4. Draw arrows
5. Review & simplify
6. Code in Mermaid
```

---

### 2. **Use Consistent Terminology**

**Good - Consistent:**
```
Login → Authenticate → Authorize → Access Dashboard
```

**Bad - Inconsistent:**
```
Log in → Auth Check → Give Permission → Show Main Page
```

**Rule:** Pick one vocabulary and stick to it.

---

### 3. **Handle Errors Explicitly**

**Good:**
```mermaid
flowchart TD
    A[Process Data]
    A --> B{Success?}
    B -->|Yes| C[Continue]
    B -->|No| D[Log Error]
    D --> E[Notify Admin]
    E --> F[Return Error]
```

**Bad:**
```mermaid
flowchart TD
    A[Process Data]
    A --> B[Continue]
```

**Rule:** Always show error paths.

---

### 4. **Avoid Crossing Lines**

**Good:**
```mermaid
flowchart TD
    A --> B
    B --> C
    C --> D
    A --> E
    E --> F
    F --> D
```

**Bad:**
```mermaid
flowchart TD
    A --> B
    B --> C
    A --> D
    D --> C
    B --> D
```

**Rule:** Rearrange nodes to minimize line crossings.

---

### 5. **Document Assumptions**

Add notes for complex flows:

```mermaid
flowchart TD
    A[Start]
    B[Process]
    C{Check}
    D[End]
    
    A --> B --> C
    C -->|Yes| D
    C -->|No| B
    
    Note["Note: Max 3 retry attempts"]
    Note -.-> B
```

---

### 6. **Version Control Flowcharts**

```markdown
# Flowchart Header Template

---
title: User Authentication Flow
version: 1.2.0
author: Development Team
date: 2025-11-06
reviewed: Security Team
status: Approved
---
```

---

## 🔁 Common Patterns

### Pattern 1: Error Handling with Retry

```mermaid
flowchart TD
    Start([Start])
    Process[Execute Task]
    Check{Success?}
    Retry{Retry < 3?}
    Increment[Increment Counter]
    Success([Success End])
    Failure([Failure End])
    
    Start --> Process
    Process --> Check
    Check -->|Yes| Success
    Check -->|No| Retry
    Retry -->|Yes| Increment
    Increment --> Process
    Retry -->|No| Failure
```

---

### Pattern 2: Validation Pipeline

```mermaid
flowchart TD
    Start([Receive Data])
    V1{Valid Format?}
    V2{Valid Range?}
    V3{Valid Business Rules?}
    Process[Process Data]
    Error[Return Error]
    Success([Success])
    
    Start --> V1
    V1 -->|No| Error
    V1 -->|Yes| V2
    V2 -->|No| Error
    V2 -->|Yes| V3
    V3 -->|No| Error
    V3 -->|Yes| Process
    Process --> Success
```

---

### Pattern 3: Async Processing

```mermaid
flowchart TD
    Start([Receive Request])
    Queue[Add to Queue]
    Response[Return Job ID]
    
    subgraph Async Processing
        Worker[Worker Picks Job]
        Process[Process Data]
        Notify[Send Notification]
    end
    
    Start --> Queue
    Queue --> Response
    Queue -.-> Worker
    Worker --> Process
    Process --> Notify
```

---

### Pattern 4: State Machine

```mermaid
flowchart LR
    Draft[Draft]
    Review[Under Review]
    Approved[Approved]
    Rejected[Rejected]
    Published[Published]
    
    Draft -->|Submit| Review
    Review -->|Approve| Approved
    Review -->|Reject| Rejected
    Rejected -->|Revise| Draft
    Approved -->|Publish| Published
    Published -->|Unpublish| Draft
```

---

## ⚠️ Anti-Patterns (What to Avoid)

### 1. **Spaghetti Flow**

**Bad:**
```mermaid
flowchart TD
    A --> B
    B --> C
    C --> D
    D --> A
    A --> E
    E --> C
    C --> F
    F --> B
    B --> G
    G --> D
```

**Fix:** Break into logical subprocesses.

---

### 2. **God Node (Too Many Connections)**

**Bad:**
```mermaid
flowchart TD
    Central[Central Process]
    A --> Central
    B --> Central
    C --> Central
    D --> Central
    Central --> E
    Central --> F
    Central --> G
    Central --> H
```

**Fix:** Use subgraphs or split into smaller flows.

---

### 3. **Ambiguous Decisions**

**Bad:**
```mermaid
flowchart TD
    A{Check Status}
    A -->|Maybe| B
    A -->|Sometimes| C
```

**Fix:** Use clear binary decisions.

```mermaid
flowchart TD
    A{Status == Active?}
    A -->|Yes| B
    A -->|No| C
```

---

### 4. **Missing End States**

**Bad:**
```mermaid
flowchart TD
    A[Start]
    B[Process]
    A --> B
```

**Fix:** Always include end nodes.

```mermaid
flowchart TD
    A([Start])
    B[Process]
    C([End])
    A --> B --> C
```

---

### 5. **Inconsistent Styling**

**Bad:** Different colors for same types of nodes.

**Fix:** Use consistent color scheme throughout project.

---

## 🛠️ Tools & Resources

### Recommended Tools

| Tool | Purpose | Link |
|------|---------|------|
| **Mermaid Live Editor** | Online editor | https://mermaid.live |
| **Draw.io** | Desktop flowcharts | https://draw.io |
| **Lucidchart** | Professional diagrams | https://lucidchart.com |
| **PlantUML** | Text-based UML | https://plantuml.com |
| **Visual Paradigm** | Enterprise modeling | https://visual-paradigm.com |

---

### VS Code Extensions

```bash
# Markdown Preview Mermaid Support
code --install-extension bierner.markdown-mermaid

# Mermaid Editor
code --install-extension tomoyukim.vscode-mermaid-editor

# Draw.io Integration
code --install-extension hediet.vscode-drawio
```

---

### CLI Tools

```bash
# Mermaid CLI (Convert to PNG/SVG)
npm install -g @mermaid-js/mermaid-cli

# Usage
mmdc -i flowchart.md -o flowchart.png

# High resolution
mmdc -i flowchart.md -o flowchart.png -w 2400 -H 1800 -s 2
```

---

### Online Resources

- **Mermaid Documentation:** https://mermaid.js.org/
- **Flowchart Best Practices:** https://creately.com/guides/flowchart-best-practices/
- **ISO 5807 Standard:** International standard for flowchart symbols
- **BPMN 2.0:** Business Process Model and Notation

---

## 📚 Examples from AI-Assistant Project

### Example 1: User Authentication Flow

```mermaid
flowchart TD
    classDef success fill:#4CAF50,stroke:#2E7D32,color:#fff
    classDef error fill:#F44336,stroke:#C62828,color:#fff
    classDef process fill:#2196F3,stroke:#1565C0,color:#fff
    
    Start([User Login Request]):::success
    ValidateInput[Validate Credentials]:::process
    CheckUser{User Exists?}
    CheckPass{Password Correct?}
    Generate[Generate JWT Token]:::process
    Return[Return Token]:::process
    ErrorUser[Error: User Not Found]:::error
    ErrorPass[Error: Invalid Password]:::error
    End([Success]):::success
    
    Start --> ValidateInput
    ValidateInput --> CheckUser
    CheckUser -->|No| ErrorUser
    CheckUser -->|Yes| CheckPass
    CheckPass -->|No| ErrorPass
    CheckPass -->|Yes| Generate
    Generate --> Return
    Return --> End
```

---

### Example 2: Text2SQL Query Processing

```mermaid
flowchart TD
    classDef input fill:#9C27B0,stroke:#6A1B9A,color:#fff
    classDef process fill:#2196F3,stroke:#1565C0,color:#fff
    classDef decision fill:#FFC107,stroke:#F57F17,color:#000
    classDef database fill:#795548,stroke:#5D4037,color:#fff
    
    Start([Receive Natural Language Query]):::input
    Parse[Parse Query with LangChain]:::process
    Validate{Valid SQL?}:::decision
    Generate[Generate SQL]:::process
    Execute[Execute Query]:::database
    Check{Results Found?}:::decision
    Format[Format Response]:::process
    Error[Return Error Message]:::process
    End([Return Results]):::input
    
    Start --> Parse
    Parse --> Generate
    Generate --> Validate
    Validate -->|No| Error
    Validate -->|Yes| Execute
    Execute --> Check
    Check -->|No| Error
    Check -->|Yes| Format
    Format --> End
    Error --> End
```

---

### Example 3: Document Intelligence OCR

```mermaid
flowchart TD
    subgraph Upload
        A([Upload File])
        B[Validate File Type]
        C{Supported?}
    end
    
    subgraph Processing
        D[Extract Text - PaddleOCR]
        E[Analyze Layout]
        F[Extract Entities]
    end
    
    subgraph Storage
        G[(Save to Database)]
        H[Generate Summary]
    end
    
    I([Return Results])
    Error[Reject File]
    
    A --> B
    B --> C
    C -->|No| Error
    C -->|Yes| D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

---

## 🎓 Learning Path

### Beginner
1. Learn basic shapes (rectangle, diamond, oval)
2. Practice simple linear flows
3. Add one decision node
4. Use Mermaid Live Editor

### Intermediate
1. Add error handling
2. Use subgraphs
3. Implement swimlanes
4. Apply color coding

### Advanced
1. Design complex state machines
2. Create reusable templates
3. Optimize for performance
4. Integrate with CI/CD

---

## ✅ Checklist for New Flowcharts

Before committing a flowchart, verify:

- [ ] Start and End nodes clearly marked
- [ ] All decision nodes have exactly 2 outputs
- [ ] All processes use "Verb + Noun" format
- [ ] No crossing lines (or minimized)
- [ ] Consistent flow direction (TD or LR)
- [ ] Error paths included
- [ ] Color scheme applied (if applicable)
- [ ] Maximum 15 nodes (or split into subprocesses)
- [ ] Mermaid syntax validated on mermaid.live
- [ ] Comments/notes for complex logic
- [ ] Version info in header
- [ ] Exported to PNG/SVG for documentation

---

## 🤝 Contributing

To add a new flowchart to AI-Assistant project:

1. **Create file:** `docs/chart_guide/examples/your-flow.md`
2. **Follow template:**
   ```markdown
   # Flow Name
   
   **Purpose:** Brief description
   **Last Updated:** YYYY-MM-DD
   **Author:** Your Name
   
   ## Diagram
   
   ```mermaid
   flowchart TD
       ...
   \```
   
   ## Description
   
   Detailed explanation...
   ```

3. **Validate:** Test on https://mermaid.live
4. **Export:** Generate PNG/SVG
5. **Commit:** Use semantic commit message
6. **PR:** Submit for review

---

## 📞 Support

For questions or suggestions:
- Create an issue: https://github.com/SkastVnT/AI-Assistant/issues
- Check examples: `./docs/chart_guide/examples/`
- Review existing diagrams: `./diagram/`

---

*Last Updated: November 6, 2025*  
*Maintained by: Development Team*
