<div align="center">

# 🔴 FraudStream
### Real-Time, Distributed Fraud Detection Engine

[![Go](https://img.shields.io/badge/Go-1.22-00ADD8.svg?style=for-the-badge&logo=go&logoColor=white)](https://go.dev/)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-FFCC01?style=for-the-badge&logo=clickhouse&logoColor=black)](https://clickhouse.com/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)

**FraudStream** is a high-throughput, low-latency event processing pipeline engineered to ingest, enrich, and mathematically score financial transactions for fraudulent behavior in under **50 milliseconds**.

Built to handle massive data skew, high concurrency, and distributed state, this system abandons traditional REST/Relational bottlenecks in favor of a strictly stateful, streaming architecture.

</div>

---

## 📈 1. The Business Imperative: Latency vs. Loss

Detecting fraud in a financial ledger is relatively straightforward when you have 24 hours to run a batch SQL query. Executing that same detection while a user waits for a payment gateway to return `200 OK` requires a deeply optimized distributed system. 

FraudStream intercepts malicious payloads *before* they hit the ledger, maintaining a near-zero false-positive rate to protect legitimate revenue while blocking automated attacks.

<div align="center">
<img width="883" height="494" alt="image" src="https://github.com/user-attachments/assets/9687266d-112f-44f8-bc2a-a7bea1fbf151" />
    </div>
### MLOps & Model Drift Management
Fraudsters adapt. A static ML model will degrade in accuracy over time. The MLOps dashboard monitors live data drift (via K-S statistics) and allows engineers to run "Shadow Deployments" (A/B testing new models against live traffic without taking blocking actions) before promoting them to production.
<div align="center">
    <img width="901" height="491" alt="image" src="https://github.com/user-attachments/assets/071c2920-19be-4f4e-9ba3-21a77ff222d8" />
</div>

### Entity Risk Management (Bust-Out Fraud)
Fraud isn't just evaluated on a per-transaction basis. FraudStream aggregates 30-day sliding windows on a per-merchant and per-user basis. This allows risk teams to instantly identify "Bust-Out Fraud"—when a dormant merchant account suddenly processes massive, anomalous volume.
<div align="center">
    <img width="888" height="486" alt="image" src="https://github.com/user-attachments/assets/46354cec-a3bd-4dbd-9cf8-c017b047585b" />
</div>


### Real-Time Threat Topology
The Next.js 14 client is not a static CRUD application. It is a live operations center connected via WebSockets, consuming materialized views from our OLAP database to visualize global network anomalies as they happen.

<div align="center">
<img width="904" height="457" alt="image" src="https://github.com/user-attachments/assets/6f83c8a4-d9f7-457d-80b2-80a12d0d4f09" />
</div>
<br>
<div align="center">
<img width="900" height="495" alt="image" src="https://github.com/user-attachments/assets/9c479f27-8a6c-4dbb-a9fb-2506a9534727" />
</div>

---

## ⚙️ 2. Macro Architecture: Decoupling Compute & State

FraudStream achieves its extreme performance by strictly isolating the ingestion layer, the stateful compute, and the analytical storage. Monolithic API designs fail under sudden traffic spikes; this architecture absorbs spikes via immutable logs.

<div align="center">
<img width="858" height="444" alt="image" src="https://github.com/user-attachments/assets/94ef60fa-45ad-4664-96f7-abf73bcc106a" />
</div>

* **Ingestion (Kafka):** Chose Apache Kafka over RabbitMQ for its disk-backed, immutable log structure. If the ML inference engine goes down, transactions queue safely via backpressure rather than crashing the payment gateway.
* **Stream Processor (Golang):** Chosen for its lightweight goroutines and high concurrency limits, allowing thousands of consumer loops to run in parallel with minimal memory footprint.

---

## ⚡ 3. The Micro Lifecycle: The 50ms Critical Path

Every network hop in this system is calculated. The system guarantees that the entire lifecycle completes within a strict 50-millisecond SLA. 

<div align="center">
<img width="871" height="295" alt="image" src="https://github.com/user-attachments/assets/56e6710c-6c19-4701-8659-4f5d64c12e4b" />
</div>

### Distributed Tracing & Observability
To enforce the 50ms budget, the pipeline implements distributed tracing (similar to Datadog/Jaeger). Every event is tagged with a trace ID, mapping the exact microsecond cost of network hops, cache hits, and database insertions.

<div align="center">
<img width="906" height="442" alt="image" src="https://github.com/user-attachments/assets/395d4792-939f-4465-a248-1c19e2b6befc" />
</div>

---

## 🧠 4. Stateful Feature Engineering & Inference

Standard REST APIs query a relational database (like PostgreSQL) for a user's history. A `SELECT COUNT(*)` query over 30 days of transactions takes 100ms+ and breaks our latency budget. 

### O(1) Sliding Windows (Redis)
FraudStream utilizes a **Redis Feature Store**. By maintaining pre-computed sliding-window aggregates (e.g., updating a `user_123_tx_count_1h` key on every write), the system retrieves the historical feature vector in `O(1)` time—usually under 2ms.

<div align="center">
<img width="897" height="390" alt="image" src="https://github.com/user-attachments/assets/ac5c997d-e7a9-4b80-83a7-d9c34b960002" />
</div>

### Mathematical Precision (XGBoost)
The XGBoost and Isolation Forest ensemble was trained against a highly imbalanced dataset of 500,000 transactions. It achieves an F1 Score of **0.919**, proving its ability to isolate fraudulent vectors mathematically without relying on generic heuristics.

<div align="center">
<img width="872" height="442" alt="image" src="https://github.com/user-attachments/assets/e430f0cc-9c02-4d3b-94b9-e47adc3d61ba" />
</div>

---

## 💾 5. High-Throughput OLAP Storage

When a transaction is blocked or cleared, it must be stored for auditing and dashboard rendering. 

### Why ClickHouse over PostgreSQL?
FraudStream flushes scored events into a **ClickHouse MergeTree** via batched inserts. Because ClickHouse stores data in columns rather than rows, the system only reads the exact columns requested by the Next.js UI. This allows for real-time aggregations (e.g., "Sum all blocked transaction amounts in Mumbai in the last 15 minutes") across hundreds of millions of records with sub-second response times.

<div align="center">
<img width="899" height="402" alt="image" src="https://github.com/user-attachments/assets/4e13f65a-b469-431b-b040-a34ba3a24457" />
</div>

---

## 🛡️ 6. Administration & Infrastructure

### Deterministic Rules Engine (Human-in-the-Loop)
Machine Learning is a black box. FraudStream mitigates business risk by wrapping the ML model in a Deterministic Rules Engine. Risk administrators can tweak XGBoost confidence intervals, IP velocity limits, and hard-block rules dynamically via the UI without restarting the Go binaries.

<div align="center">
<img width="873" height="481" alt="image" src="https://github.com/user-attachments/assets/f12bbfd0-0795-4913-ba52-708b95af60dd" />
</div>

### Benchmarks & CI/CD
Benchmarked on a localized Docker cluster, the Go-based processor safely sustains **12,450 TPS (Transactions Per Second)** before backpressure triggers Kafka queue buffering. All code is verified via GitHub Actions before being pushed to an image registry for zero-downtime Kubernetes deployments.

<div align="center">
<img width="872" height="400" alt="image" src="https://github.com/user-attachments/assets/c835c861-804b-439a-928c-c9f7a9bcbf08" />
</div>
<br>
<div align="center">
<img width="887" height="345" alt="image" src="https://github.com/user-attachments/assets/cb465db3-9001-480c-8c67-b55dfbe02780" />
</div>

---

## 🚀 7. Local Cluster Setup

Spin up the entire distributed environment locally using Docker. (Requires minimum 4GB RAM allocated to Docker Engine).

```bash
# 1. Clone the repository
git clone [https://github.com/sat1828/FraudStream.git](https://github.com/sat1828/FraudStream.git)
cd FraudStream

# 2. Boot the infrastructure (Kafka, Zookeeper, Redis, ClickHouse)
docker-compose up -d

# 3. Start the Golang Producer (Simulates live payment traffic)
cd producer && go run main.go

# 4. Start the Golang Stream Processor & Python Inference Node
cd processor && python main.py

# 5. Launch the Next.js Dashboard
cd frontend && npm run dev
