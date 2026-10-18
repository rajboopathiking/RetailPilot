# Client brief: Northstar Commerce / RetailPilot

## Client request
> We operate an Indian e-commerce storefront with electronics, home, fashion and fitness products. Our frontline team repeatedly handles “where is my order?”, “can I return this?”, and “has my refund arrived?” questions. Shoppers also ask for comparable products and current inventory. Our business users need trustworthy answers about monthly sales without granting a chatbot access to modify the database. Build us a safe AI copilot embedded in the store.

## Existing pain points (fictional baseline assumptions; not measured facts)
- 1,200 support contacts/week; 55% are repetitive status or policy inquiries.
- Mean human first-response time: 18 minutes; first-contact resolution: 62%.
- Product-search-to-add-to-cart rate: 7%; support cost: ₹62/ticket.
- Analysts manually produce reports; turnaround 1–2 business days.

## 30-day pilot targets
- Automate ≥35% of eligible repetitive support intents, with ≥95% factual accuracy on audited pilot conversations.
- 0 cross-customer order disclosures and 0 unsafe SQL executions in the test suite.
- ≥90% correct agent routing on a representative labeled set.
- ≥90% correct product/stock grounding; stock = SUM(on_hand - reserved).
- P95 API latency ≤5 seconds on a controlled development benchmark (excluding external model outages).
- Cut analyst-style revenue query turnaround to <30 seconds in a staged demonstration.

## Personas
**Guest shopper:** browses inventory and asks general policies, cannot access orders.
**Authenticated shopper:** can view own orders, shipment, returns, policies.
**Merchandising associate:** asks aggregated product and sales questions; must not receive customer PII.
**Support lead:** reviews traces, deflections, escalations and factual correctness.

## Required demo journeys
1. Authenticated order tracking plus precise status.
2. Return policy Q&A using retrieved KB and citation.
3. Refund status query that distinguishes pending vs completed.
4. Product comparison under a price ceiling and stock check.
5. SQL-backed category sales report with safely joined tables.
6. Router handles mixed support/sales prompts and unsupported requests.
7. Negative tests: cross-account lookup, SQL injection, prompt injection, impossible stock/refund claims.

## In-scope architecture
FastAPI; LangGraph router/state; Support agent with LlamaIndex policy RAG and customer-scoped read-only APIs; Sales agent with product search, inventory and allowlisted SQL; SQLite + local vector index; OpenTelemetry/LangSmith or similar tracing; golden-set evaluations; lightweight web chat UI.

## Non-functional design
- Authentication belongs to the backend: never trust a user-message customer ID. For demo only, a mock login may select a user; production requires verified session/JWT.
- All SQL and operational tools are read-only; apply per-tool allowlists, timeouts, row caps and DB credentials with SELECT permissions.
- Separate evaluation access from end-user production access. Reporting tools should expose aggregates only.
- RAG sources: only curated Markdown KB and catalog, never the whole private customer table.
- Clear escalation when policies are ambiguous or account actions are not supported.

## Delivery plan (7 days)
**Day 1:** load DB, validate joins, design endpoint and auth scope.
**Day 2:** implement deterministic order, shipment, returns, inventory tools.
**Day 3:** build policy RAG + product discovery with citations.
**Day 4:** implement LangGraph router and specialist nodes.
**Day 5:** integrate SQL guardrails + FastAPI + web chat.
**Day 6:** implement traces, run golden tests and failure analysis.
**Day 7:** deploy demo, record metrics, write customer handoff and architecture decision log.

## Out of scope
Actual order cancellation, payment/refund execution, production PII, recommendations based on private browsing history, live courier APIs, CRM write access.

## Dataset caveats
Synthetic records are internally related but not a faithful model of any actual company. Timestamps and business events are generated, so operational constraints must be validated before pretending this is a production ledger. Shipping dates are illustrative; demo must not treat them as live courier promises.
