# Prompt Bridge

Professional AI proxy platform with browser automation and multi-provider support.

## Features

- 🚀 **OpenAI-Compatible API** - Drop-in replacement for OpenAI's chat completions
- 🎭 **Stealth Browser Automation** - Bypass Cloudflare and anti-bot protections
- 🔄 **Session Pool Management** - 10x faster response times with browser reuse
- 🌐 **Multi-Provider Support** - ChatGPT, Qwen AI, and extensible provider registry
- 🛡️ **Production Resilience** - Retry logic, circuit breakers, graceful degradation
- 📊 **Comprehensive Observability** - Structured logging, Prometheus metrics, tracing
- 🎨 **Rich CLI Experience** - Colorized status commands and developer tools
- 🐳 **Production Ready** - Docker, Kubernetes, graceful shutdown, health checks
- 🌊 **Streaming Support** - Server-Sent Events (SSE) for real-time response streaming (in development)

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (install via pip, homebrew, or [official guide](https://docs.astral.sh/uv/getting-started/installation/))

### Installation

```bash
# Clone the repository
git clone https://github.com/sabry-awad97/prompt_bridge.git
cd prompt_bridge

# Install dependencies
uv sync                    # Production dependencies
uv sync --extra dev        # Include dev dependencies

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Run the server
uv run prompt-bridge start
```

### CLI Commands

```bash
# Server Management
uv run prompt-bridge start              # Start server
uv run prompt-bridge start --reload     # Start with hot reload

# Monitoring & Health
uv run prompt-bridge status             # Show system status with provider health
uv run prompt-bridge health             # Run health checks on server and providers
uv run prompt-bridge logs               # Show recent logs with syntax highlighting

# Information
uv run prompt-bridge version            # Show version information
uv run prompt-bridge --help             # Show all available commands

# Global Options
uv run prompt-bridge --config config.toml  # Use custom config file
uv run prompt-bridge --verbose             # Enable verbose output
```

### API Usage

```python
import httpx

# OpenAI-compatible chat completion
response = httpx.post(
    "http://localhost:7777/v1/chat/completions",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)

# Streaming support (in development)
# Set "stream": true for Server-Sent Events (SSE) streaming
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --extra dev

# Install pre-commit hooks (if configured)
uv run pre-commit install

# Run with hot reload
uv run prompt-bridge start --reload
```

### Code Quality

```bash
# Linting
uv run ruff check .                     # Check for issues
uv run ruff check --fix .               # Auto-fix issues

# Formatting
uv run ruff format .                    # Format code
uv run ruff format --check .            # Check formatting without changes

# Type Checking
uv run ty check                         # Run type checker
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test suites
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/integration/        # Integration tests only
uv run pytest tests/smoke/ -m smoke     # Smoke tests (requires real browsers)

# Test with coverage
uv run pytest --cov=prompt_bridge --cov-report=html

# Run specific test
uv run pytest -k test_name              # Run tests matching pattern

# Verbose output
uv run pytest -v                        # Verbose test output
```

### Adding Dependencies

```bash
# Add production dependency (gets latest version)
uv add <package>

# Add development dependency
uv add --dev <package>

# Add specific version (only if required)
uv add <package>==<version>
```

### Build & Install

```bash
# Build package
uv build

# Install in editable mode
uv pip install -e .
```

## Project Structure

```
prompt_bridge/
├── src/prompt_bridge/
│   ├── domain/          # Pure business logic (no dependencies)
│   ├── application/     # Use cases and orchestration
│   ├── infrastructure/  # External dependencies (browser, providers)
│   ├── presentation/    # API routes, DTOs, HTTP concerns
│   └── cli/            # Command-line interface
├── tests/              # Test suite (unit, integration, smoke)
├── config*.toml        # Configuration files
└── docs/              # Documentation and issue tracking
```

### Architecture Principles

Prompt Bridge follows **Clean Architecture** principles:

- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: Use cases and business logic orchestration
- **Infrastructure Layer**: External dependencies (browsers, databases, APIs)
- **Presentation Layer**: HTTP API, CLI, and user interfaces

Each feature is implemented as a **vertical slice** that cuts through all layers end-to-end for immediate value delivery.

## Configuration

Configuration is managed through TOML files with environment variable overrides:

- `config.toml` - Default settings
- `config.development.toml` - Development overrides
- `config.production.toml` - Production overrides
- `.env` - Environment variables (secrets)

### Key Configuration Sections

```toml
[server]
host = "0.0.0.0"
port = 7777
workers = 1

[browser]
headless = true
timeout = 120
solve_cloudflare = true
real_chrome = true

[session_pool]
pool_size = 3
max_session_age = 3600  # 1 hour
acquire_timeout = 30

[resilience]
max_retry_attempts = 3
retry_backoff_base = 2.0
circuit_breaker_failure_threshold = 5
circuit_breaker_timeout = 60

[observability]
log_level = "INFO"
structured_logging = true
metrics_enabled = true
tracing_enabled = false

[providers]
chatgpt_enabled = true
qwen_enabled = false
```

## Architecture

Prompt Bridge follows Clean Architecture principles:

- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: Use cases and business logic orchestration
- **Infrastructure Layer**: External dependencies (browsers, databases, APIs)
- **Presentation Layer**: HTTP API, CLI, and user interfaces

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch

   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Follow the development workflow**:
   - Check `docs/issues/` for vertical slice issues
   - Add dependencies using `uv add <package>` for latest versions
   - Follow Clean Architecture layers (Domain → Application → Infrastructure → Presentation)
   - Write tests for new functionality

3. **Ensure code quality**:

   ```bash
   uv run ruff format .           # Format code
   uv run ruff check --fix .      # Fix linting issues
   uv run ty check                # Type check
   uv run pytest                  # Run tests
   ```

4. **Commit and push**:

   ```bash
   git commit -m 'Add amazing feature'
   git push origin feature/amazing-feature
   ```

5. **Open a Pull Request** with a clear description of changes

### Development Standards

- **Test Coverage**: Aim for 90% on business logic
- **Type Safety**: Full type hints with ty strict mode
- **Code Style**: Follow ruff formatting and linting rules
- **Architecture**: Maintain Clean Architecture separation of concerns

## Roadmap

### Current Features

- ✅ OpenAI-compatible API
- ✅ ChatGPT and Qwen provider support
- ✅ Session pool management
- ✅ Circuit breakers and retry logic
- ✅ Comprehensive observability
- ✅ Rich CLI experience

### In Development

- 🚧 Server-Sent Events (SSE) streaming support
- 🚧 Real-time response streaming
- 🚧 Streaming configuration and monitoring
- 🚧 Enhanced performance metrics

See `docs/issues/` for detailed implementation plans.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/sabry-awad97/prompt_bridge/issues)
- 💬 [Discussions](https://github.com/sabry-awad97/prompt_bridge/discussions)
