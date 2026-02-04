# System Architecture & Technical Stack Analysis

## 🏗️ Architecture Flow Diagram

The following diagram illustrates the traffic flow designed to bypass Gemini's geolocation restrictions while maintaining a cost-effective host in Singapore.

```mermaid
---
config:
  theme: dark
  themeVariables:
    darkMode: true
---
graph TD
    User([User]) <-->|HTTPS| UI[Streamlit UI]
    UI <-->|REST API| API[FastAPI Backend]
    subgraph Singapore_Infra ["Singapore Infrastructure (Restricted IP)"]
        direction TB
        
        API
        subgraph Agent_Workflow ["LangGraph Agent Orchestrator"]
            Start((Start)) --> Route{Route Input}
            Route -->|Video| VidProc["Process Video\n(Frames -> Text)"]
            Route -->|Text| CheckCache{Check Cache}
            VidProc --> CheckCache
            
            CheckCache -->|Hit| End((End))
            CheckCache -->|Miss| VecSearch["Vector Search\n(MongoDB Atlas)"]
            
            VecSearch --> GenKnow{Need Knowledge?}
            GenKnow -->|Yes| Gen["Generate & Ingest\nKnowledge"]
            GenKnow -->|No| Final[Final Analysis]
            Gen --> Final
            
            Final --> Cache["Cache Result\n(Redis)"]
            Cache --> End
        end
        Redis[(Redis Cache)]
        Mongo[("MongoDB Atlas\nVector Store")]
        CheckCache -.->|Get| Redis
        Cache -.->|Set| Redis
        VecSearch <-->|Query/Docs| Mongo
        Gen -->|Upsert| Mongo
    end
    subgraph Google_Cloud_Platform ["Google Cloud Platform (US-Central1)"]
        Proxy[("Cloud Run Proxy\n(Stateless Forwarder)")]
    end
    subgraph External_Services ["Google AI Services"]
        Gemini[("Gemini API\n(Flash/Pro/Vision)")]
    end
    subgraph Observability ["Observability Layer"]
        Collector[("Jaeger All-In-One\n(Collector + UI + Store)")]
    end
    VidProc -->|1. Vision Request| Proxy
    Gen -->|2. Generate Request| Proxy
    Final -->|3. Analysis Request| Proxy
    
    Proxy <-->|Forward via US IP| Gemini
    API -.->|OTLP HTTP/gRPC| Collector
    Start -.->|Trace Context| Collector
    
    
    classDef darkNode fill:#1a1a1a,stroke:#66b3ff,stroke-width:2px,color:#fff;
    classDef darkCluster fill:#0d1117,stroke:#30363d,stroke-width:2px,color:#fff;
    
    style Singapore_Infra fill:#1f1300,stroke:#ff9900,stroke-width:2px,stroke-dasharray: 5 5,color:#fff
    style Agent_Workflow fill:#2d1b00,stroke:#ffaa00,stroke-width:2px,color:#fff
    style Google_Cloud_Platform fill:#001a33,stroke:#3399ff,stroke-width:2px,color:#fff
    style External_Services fill:#002200,stroke:#33cc33,stroke-width:2px,color:#fff
    style Observability fill:#2c001e,stroke:#ff0066,stroke-width:2px,color:#fff
    style Collector fill:#660033,stroke:#ff3399,color:#fff
    
    style Proxy fill:#003366,stroke:#66b3ff,stroke-width:4px,color:#fff
    style Redis fill:#330000,stroke:#ff6666,color:#fff
    style Mongo fill:#003300,stroke:#66ff66,color:#fff
    style User color:#fff,stroke:#fff
    style UI color:#000,stroke:#fff,fill:#ccc
    style API color:#000,stroke:#fff,fill:#ccc
    style Start color:#fff,stroke:#fff,fill:#333
    style End color:#fff,stroke:#fff,fill:#333
    style Route color:#fff,stroke:#fff,fill:#333
    style VidProc color:#fff,stroke:#fff,fill:#333
    style CheckCache color:#fff,stroke:#fff,fill:#333
    style VecSearch color:#fff,stroke:#fff,fill:#333
    style GenKnow color:#fff,stroke:#fff,fill:#333
    style Gen color:#fff,stroke:#fff,fill:#333
    style Final color:#fff,stroke:#fff,fill:#333
    style Cache color:#fff,stroke:#fff,fill:#333
```

---

## 🛠️ Technical Stack Recommendation

Based on the expanded architecture (including the Agentic workflow and UI), here is the validation of the full stack:

### 1. **Orchestration: LangGraph (Agentic Workflow)**
*   **Why it fits:** The diagram shows a complex, multi-step decision process (Video? Cache? Search? Knowledge?). **LangGraph** is superior to simple chains because it offers **stateful, cyclic execution**. It allows the agent to "loop back" if more knowledge is needed or exit early on a cache hit, providing significantly better control than a linear DAG.
*   **Verdict:** ✅ **Critical for Logic**. Enables the "smart" behavior of the agent.

### 2. **Frontend: Streamlit**
*   **Why it fits:** For internal tools or data-heavy apps like CareerPilot, React/Next.js is often overkill. **Streamlit** allows building the UI entirely in Python, tightly coupling it with the backend data models.
*   **Verdict:** ✅ **High Velocity**. Perfect for rapid iteration on prompt engineering and UX without context switching languages.

### 3. **Data Layer: Hybrid (Redis + MongoDB)**
*   **Redis (Caching):** Essential for cost and latency. By caching final analysis results, you avoid expensive re-runs of the Vision/Pro models.
*   **MongoDB Atlas (Vector Store):** A unified NoSQL + Vector database. It avoids the complexity of managing a separate Pinecone/Milvus instance, keeping the infra footprint small (Critical for the single-node k3s setup).
*   **Verdict:** ✅ **Efficient & Compact**.

### 4. **Compute & Networking: k3s + Cloud Run Proxy**
*   **Why it fits:** Maintains the cost benefits of the Singapore VPS while legally bypassing the IP restrictions via the US-based stateless proxy.
*   **Verdict:** ✅ **Best in Class for this constraint**.

### 5. **Observability: OpenTelemetry + SigNoz**
*   **Why it fits:** The agentic workflow is non-deterministic and hard to debug with simple logs. **OpenTelemetry** provides distributed tracing to visualize the full request lifecycle from API to Proxy to Gemini. **SigNoz** (or Jaeger) gives a UI to inspect these traces.
*   **Verdict:** ✅ **Day 2 Operation Requirement**. Essential for production debugging.

---

## 🔑 Key "Suitability" Factors for This Use Case

| Feature | Why this stack is the best fit |
| :--- | :--- |
| **Complex Decision Making** | **LangGraph** enables the agent to dynamically decide between Video/Text paths and whether to generate new knowledge, rather than following a rigid script. |
| **Solving the Geo-Block** | The **Cloud Run Proxy** acts as a legal "jumphost," removing IP reputation risks from the Singapore data center. |
| **Rapid Prototyping** | **Streamlit** + **FastAPI** allows for immediate feedback loops on AI responses without frontend overhead. |
| **Cost Efficiency** | Using **Redis** to intercept requests before they hit Gemini saves significant token costs on repeated queries. |
| **Full Visibility** | **OpenTelemetry** helps identify bottlenecks in the multi-step agent chain (e.g., "Why did Vector Search take 3s?"). |

### 🚀 Summary
This architecture has evolved from a simple API wrapper to a **Stateful, Intelligent Agent System**. It balances the **complexity** of AI orchestration (handled by LangGraph) with the **simplicity** of infrastructure (k3s + MongoDB). The result is a robust, production-capable system running on minimal resources.
