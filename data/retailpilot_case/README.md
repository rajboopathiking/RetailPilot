# RetailPilot — E-commerce AI Customer & Sales Copilot

**Fictional client:** Northstar Commerce Pvt Ltd (India), an online multi-category retailer.

**Business problem:** The retailer receives repetitive order/refund queries while shoppers abandon product discovery. Support agents switch between order tools and policy documents; sales teams manually query product, inventory and revenue tables. The company needs one audited chat interface that can route questions to two specialist agents, ground answers in approved knowledge, and safely access transactional data.

**Your role:** Forward Deployed AI Engineer hired to deliver an integrated, testable pilot in one repository.

## Project outcome / acceptance criteria
1. One FastAPI `/chat` endpoint accepts `session_id`, `authenticated_customer_id` (nullable), and `message`; returns answer, selected agent, source IDs, tool calls, trace ID.
2. LangGraph routes **support** vs **sales** queries, maintains conversation context, and allows a safe no-tool response.
3. Support agent can retrieve authenticated order, shipment, and return status and answer policy FAQs through LlamaIndex RAG. Never disclose another customer's order.
4. Sales agent discovers / compares products, computes inventory availability, and runs allowlisted **read-only** SQL reporting queries. SQL must be parameterized where possible, scoped to reporting views/tables, limited in rows/time, and reject DDL/DML/PII extraction.
5. Answers distinguish static FAQ from dynamic transactional facts; give KB document IDs for policy answers. Do not hallucinate refunds, discounts, delivery dates, or stocks.
6. Traces record routing, tools, latency, exceptions and retrieved documents without customer PII. Run and score provided golden tests, including hostile prompts.
7. Deploy API + web demo + database with repeatable setup; include local README, env example and short customer-facing demo.

## Data pack
- `retailpilot.db`: ready-to-query SQLite database, foreign keys + indexes.
- `data/*.csv`: identical relational tables for inspection or Postgres migration.
- `knowledge/*.md`: curated policy documents for RAG indexing.
- `evals/golden_tests.csv`: 12 grounded test prompts with expected behavior (not precomputed answer text).
- `docs/problem_statement.md`: project scope, business KPIs, scenarios and milestones.
- `docs/example_queries.sql`: validated starting point for reporting.

Currency INR. Data is **100% synthetic** and intentionally uses reserved `example.test` emails. Snapshot is 2026-10-15, with historical order records beginning Jan 2026. All company claims and policies are fictional.

## Tables & relationships
`customers (1) → orders (N) → order_items (N) → products (1)`; `orders → payments / shipments / returns`; `products → inventory (by warehouse)`; `customers → support_tickets`; `knowledge_base` mirrors policy Markdown. Note returns additionally identify the associated order item.

## First run
```bash
python -m sqlite3 retailpilot.db 'SELECT status, COUNT(*) FROM orders GROUP BY status;'
```
If your Python does not support the CLI, run `sqlite3 retailpilot.db` and execute the query.

## Architecture
`Web Chat → FastAPI → LangGraph Router → [Support Agent: LlamaIndex policies + authenticated order tools | Sales Agent: Product RAG + inventory + safe reporting SQL] → SQLite / vector index → traces + evals`.

**Scope:** Pilot only; no real payment collection, no automated refunds/cancellations, no admin mutation tools, no real customer identities.
