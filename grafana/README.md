# Grafana Dashboards

Pre-built Grafana dashboards for monitoring your FastAPI application.

## Available Dashboards

### 1. API Overview (`api-overview.json`)

Monitor HTTP request metrics:
- Request rate (requests/second)
- P95 latency
- Error rate (5xx responses)
- Requests in progress
- Request rate by HTTP method
- Latency percentiles (P50, P90, P95, P99)
- Request rate by status code
- Top 10 endpoints by request rate

### 2. Database & Redis (`database-redis.json`)

Monitor data layer performance:
- Active database connections
- P95 query latency
- Database error rate
- Query rate
- Connection pool status (active, idle, overflow)
- Query latency percentiles
- Queries by operation type (SELECT, INSERT, UPDATE, DELETE)
- Cache hit rate
- Redis connections
- Cache hits vs misses

### 3. Business Metrics (`business-metrics.json`)

Monitor business KPIs:
- Total users
- Active users
- Active subscriptions
- Logins per hour
- Subscriptions by plan (pie chart)
- Daily signups trend
- Background job queue size
- Jobs completed/failed per second
- P95 job duration
- Job status over time
- LLM request rate
- Token usage rate
- LLM latency
- LLM error rate
- Token usage by type (prompt/completion)
- LLM requests by provider/model

## Installation

### Option 1: Import via Grafana UI

1. Open Grafana and go to **Dashboards** → **Import**
2. Upload the JSON file or paste the JSON content
3. Select your Prometheus datasource
4. Click **Import**

### Option 2: Provisioning (Recommended for Production)

Create a provisioning configuration in `/etc/grafana/provisioning/dashboards/`:

```yaml
# /etc/grafana/provisioning/dashboards/fastapi.yaml
apiVersion: 1
providers:
  - name: 'FastAPI Dashboards'
    orgId: 1
    folder: 'FastAPI'
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards/fastapi
```

Copy the dashboard JSON files to `/var/lib/grafana/dashboards/fastapi/`.

### Option 3: Docker Compose

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    ports:
      - "3000:3000"
```

Create `grafana/provisioning/dashboards/default.yaml`:

```yaml
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
```

## Configuration

### Variables

Each dashboard includes configurable variables:

- **datasource**: Select your Prometheus datasource
- **job**: Filter by Prometheus job label (defaults to `omnistack-api`)

### Prometheus Job Configuration

Ensure your Prometheus scrape config includes the correct job name:

```yaml
scrape_configs:
  - job_name: 'omnistack-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/public/metrics'
```

## Metrics Required

These dashboards expect the following metrics from your application:

### Request Metrics
- `http_requests_total{method, endpoint, status_code}`
- `http_request_duration_seconds{method, endpoint}`
- `http_requests_in_progress{method, endpoint}`

### Database Metrics
- `db_queries_total{operation, table}`
- `db_query_duration_seconds{operation, table}`
- `db_pool_connections{state}`
- `db_errors_total{error_type}`

### Cache Metrics
- `cache_hits_total{cache_type}`
- `cache_misses_total{cache_type}`
- `redis_connections`

### Business Metrics
- `users_total{status}`
- `active_subscriptions_total{plan}`
- `auth_events_total{event, provider}`

### Job Metrics
- `background_jobs_total{job_name, status}`
- `background_job_duration_seconds{job_name}`
- `background_job_queue_size{queue_name}`

### AI/LLM Metrics
- `llm_requests_total{provider, model, status}`
- `llm_tokens_total{provider, model, type}`
- `llm_request_duration_seconds{provider, model}`

## Customization

### Adding Alerts

You can add alert rules to any panel:

1. Edit the panel
2. Go to **Alert** tab
3. Configure alert conditions and notifications

### Common Alert Examples

```yaml
# High Error Rate
- alert: HighErrorRate
  expr: sum(rate(http_requests_total{status_code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"

# High Latency
- alert: HighLatency
  expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P95 latency exceeds 1 second"

# Database Pool Exhausted
- alert: DatabasePoolExhausted
  expr: db_pool_connections{state="overflow"} > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Database connection pool overflow"
```

## Troubleshooting

### No Data Showing

1. Verify Prometheus is scraping your metrics endpoint:
   ```bash
   curl http://localhost:8000/api/v1/public/metrics
   ```

2. Check Prometheus targets are healthy:
   - Go to Prometheus UI → Status → Targets

3. Verify the job label matches your scrape config

### Metrics Not Found

Ensure `prometheus-client` is installed:
```bash
pip install prometheus-client
```

And that metrics collection is enabled in your app.
