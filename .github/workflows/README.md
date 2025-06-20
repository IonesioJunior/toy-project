# GitHub Actions Code Quality Workflow

This workflow runs comprehensive code quality checks on pull requests.

## Features

### 1. SonarCloud Analysis (Optional)
- Runs static code analysis using SonarCloud
- Requires `SONAR_TOKEN` secret to be configured
- Automatically skipped if token is not available
- Analyzes code quality, security issues, and technical debt

### 2. Coverage Report
- Runs the complete test suite with coverage tracking
- Generates coverage reports in multiple formats (XML, HTML, terminal)
- Comments on the PR with coverage changes
- **Fails if coverage drops below 80%**
- Uploads coverage artifacts for download

### 3. Performance Testing
- Uses Locust for load testing key API endpoints
- Simulates multiple user types (regular users, admins, stress testing)
- Tests include:
  - Health check endpoint
  - File listing and upload
  - Permission management
  - Response time metrics
- **Fails if average response time exceeds 1 second**
- **Fails if 95th percentile exceeds 2 seconds**
- Generates performance reports and artifacts

## Setup

### Required Secrets
- `SONAR_TOKEN` (optional): Token for SonarCloud analysis

### Performance Test Configuration
The performance tests simulate three user types:
1. **ToyProjectUser**: Regular user behavior (file operations, permissions)
2. **AdminUser**: Admin-specific patterns (dashboard, bulk operations)
3. **APIStressTest**: High-frequency requests for stress testing

### Thresholds
- **Coverage**: Minimum 80% code coverage required
- **Performance**: 
  - Average response time: < 1000ms
  - 95th percentile: < 2000ms
  - Zero failures tolerated

## Running Locally

### Coverage Testing
```bash
uv run pytest --cov=app --cov-report=term --cov-report=html
```

### Performance Testing
```bash
# Start your application
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, run Locust
uv run locust -f test/performance/locustfile.py --host http://localhost:8000
```

## Artifacts
The workflow generates the following artifacts:
- **coverage-reports**: Coverage XML, HTML reports, and badge
- **performance-reports**: Locust HTML report and CSV results