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

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd prompt_bridge

# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Run the server
uv run prompt-bridge start
```

### Usage

```bash
# Start the server
uv run prompt-bridge start

# Check system status
uv run prompt-bridge status

# Run health checks
uv run prompt-bridge health

# View help
uv run prompt-bridge --help
```

### API Usage

```python
import httpx

# OpenAI-compatible chat completion
response = httpx.post("http://localhost:7777/v1/chat/completions",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run with hot reload
uv run prompt-bridge start --reload
```

### Project Structure

```
prompt_bridge/
├── src/prompt_bridge/
│   ├── domain/          # Pure business logic
│   ├── application/     # Use cases and orchestration
│   ├── infrastructure/  # External dependencies
│   ├── presentation/    # API routes and DTOs
│   └── cli/            # Command-line interface
├── tests/              # Test suite
├── config*.toml        # Configuration files
└── docs/              # Documentation
```

### Running Tests

```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# Smoke tests (requires real browsers)
uv run pytest tests/smoke/ -m smoke

# All tests with coverage
uv run pytest --cov=prompt_bridge --cov-report=html
```

## Configuration

Configuration is managed through TOML files with environment variable overrides:

- `config.toml` - Default settings
- `config.development.toml` - Development overrides
- `config.production.toml` - Production overrides
- `.env` - Environment variables (secrets)

## Architecture

Prompt Bridge follows Clean Architecture principles:

- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: Use cases and business logic orchestration
- **Infrastructure Layer**: External dependencies (browsers, databases, APIs)
- **Presentation Layer**: HTTP API, CLI, and user interfaces

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the coding standards
4. Run tests (`uv run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/prompt-bridge/issues)
- 💬 [Discussions](https://github.com/your-org/prompt-bridge/discussions)
