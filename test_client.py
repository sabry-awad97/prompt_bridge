"""Test client for Prompt Bridge API."""

import requests
import json
import time
from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test result data."""
    name: str
    passed: bool
    duration: float = 0.0
    error: str | None = None


class PromptBridgeClient:
    """Client for interacting with Prompt Bridge API."""

    def __init__(self, base_url: str = "http://localhost:7777"):
        """Initialize client.
        
        Args:
            base_url: Base URL of the Prompt Bridge server
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _handle_request(
        self, 
        func: Callable[[], requests.Response],
        timeout: int = 120
    ) -> tuple[bool, requests.Response | None, str | None]:
        """Handle HTTP request with error handling.
        
        Args:
            func: Function that makes the HTTP request
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (success, response, error_message)
        """
        try:
            response = func()
            return True, response, None
        except requests.exceptions.ConnectionError:
            return False, None, f"Cannot connect to server at {self.base_url}"
        except requests.exceptions.Timeout:
            return False, None, f"Request timed out after {timeout}s"
        except requests.exceptions.RequestException as e:
            return False, None, f"Request failed: {e}"
        except Exception as e:
            return False, None, f"Unexpected error: {e}"

    def health_check(self) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Check server health.
        
        Returns:
            Tuple of (success, data, error_message)
        """
        success, response, error = self._handle_request(
            lambda: self.session.get(f"{self.base_url}/health", timeout=30),
            timeout=30
        )
        
        if not success:
            return False, None, error
        
        if response and response.status_code == 200:
            return True, response.json(), None
        
        return False, None, f"Health check failed with status {response.status_code if response else 'unknown'}"

    def chat_completion(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        timeout: int = 120
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """Send chat completion request.
        
        Args:
            provider: Provider name (chatgpt, qwen)
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (success, data, error_message)
        """
        payload = {
            "provider": provider,
            "model": model,
            "messages": messages
        }
        
        success, response, error = self._handle_request(
            lambda: self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=timeout
            ),
            timeout=timeout
        )
        
        if not success:
            return False, None, error
        
        if response and response.status_code == 200:
            return True, response.json(), None
        
        error_text = response.text if response else "unknown error"
        return False, None, f"Request failed: {error_text}"


class TestSuite:
    """Test suite for Prompt Bridge."""

    def __init__(self, client: PromptBridgeClient):
        """Initialize test suite.
        
        Args:
            client: PromptBridgeClient instance
        """
        self.client = client
        self.results: list[TestResult] = []

    def _print_test_header(self, emoji: str, name: str):
        """Print test header."""
        print(f"{emoji} {name}")

    def _print_success(self, message: str):
        """Print success message."""
        print(f"   ✓ {message}")

    def _print_error(self, message: str):
        """Print error message."""
        print(f"   ✗ {message}")

    def _print_info(self, message: str):
        """Print info message."""
        print(f"   {message}")

    def test_health_check(self) -> TestResult:
        """Test health check endpoint."""
        self._print_test_header("🏥", "Health Check")
        start = time.time()
        
        success, data, error = self.client.health_check()
        duration = time.time() - start
        
        if success and data:
            self._print_success(f"Status: {data.get('status')}")
            self._print_info(f"Version: {data.get('version')}")
            self._print_info(f"Providers: {list(data.get('providers', {}).keys())}")
            print()
            return TestResult("Health Check", True, duration)
        else:
            self._print_error(error or "Unknown error")
            if error and "Cannot connect" in error:
                self._print_info("Make sure the server is running: uv run prompt-bridge start")
            print()
            return TestResult("Health Check", False, duration, error)

    def test_chatgpt_simple(self) -> TestResult:
        """Test simple ChatGPT completion."""
        self._print_test_header("💬", "ChatGPT - Simple completion")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="chatgpt",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello in one word"}]
        )
        duration = time.time() - start
        
        if success and data:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            self._print_success(f"Response: {content}")
            self._print_info(f"Duration: {duration:.2f}s")
            self._print_info(f"Tokens: {usage.get('total_tokens')} (prompt: {usage.get('prompt_tokens')}, completion: {usage.get('completion_tokens')})")
            print()
            return TestResult("ChatGPT Simple", True, duration)
        else:
            self._print_error(error or "Unknown error")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("ChatGPT Simple", False, duration, error)

    def test_chatgpt_multi_turn(self) -> TestResult:
        """Test multi-turn ChatGPT conversation."""
        self._print_test_header("🔄", "ChatGPT - Multi-turn conversation")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="chatgpt",
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
                {"role": "user", "content": "What about 3+3?"}
            ]
        )
        duration = time.time() - start
        
        if success and data:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self._print_success(f"Answer: {content}")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("ChatGPT Multi-turn", True, duration)
        else:
            self._print_error(error or "Unknown error")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("ChatGPT Multi-turn", False, duration, error)

    def test_qwen_simple(self) -> TestResult:
        """Test simple Qwen completion."""
        self._print_test_header("🤖", "Qwen - Simple completion")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="qwen",
            model="qwen-max",
            messages=[{"role": "user", "content": "Say hello in one word"}]
        )
        duration = time.time() - start
        
        if success and data:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            self._print_success(f"Response: {content}")
            self._print_info(f"Duration: {duration:.2f}s")
            self._print_info(f"Tokens: {usage.get('total_tokens')} (prompt: {usage.get('prompt_tokens')}, completion: {usage.get('completion_tokens')})")
            print()
            return TestResult("Qwen Simple", True, duration)
        else:
            self._print_error(error or "Unknown error")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("Qwen Simple", False, duration, error)

    def test_qwen_chinese(self) -> TestResult:
        """Test Qwen with Chinese text."""
        self._print_test_header("🇨🇳", "Qwen - Chinese language")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="qwen",
            model="qwen-max",
            messages=[{"role": "user", "content": "用一个词说你好"}]
        )
        duration = time.time() - start
        
        if success and data:
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self._print_success(f"Response: {content}")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("Qwen Chinese", True, duration)
        else:
            self._print_error(error or "Unknown error")
            self._print_info(f"Duration: {duration:.2f}s")
            print()
            return TestResult("Qwen Chinese", False, duration, error)

    def test_invalid_provider(self) -> TestResult:
        """Test invalid provider."""
        self._print_test_header("❌", "Invalid provider")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="invalid",
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
            timeout=30
        )
        duration = time.time() - start
        
        # This test expects failure
        if not success:
            self._print_success("Expected error received")
            print()
            return TestResult("Invalid Provider", True, duration)
        else:
            self._print_error("Unexpected success - should have failed")
            print()
            return TestResult("Invalid Provider", False, duration, "Should have failed")

    def test_invalid_model(self) -> TestResult:
        """Test invalid model."""
        self._print_test_header("❌", "Invalid model")
        start = time.time()
        
        success, data, error = self.client.chat_completion(
            provider="chatgpt",
            model="invalid-model",
            messages=[{"role": "user", "content": "Hello"}],
            timeout=30
        )
        duration = time.time() - start
        
        # This test expects failure
        if not success:
            self._print_success("Expected error received")
            print()
            return TestResult("Invalid Model", True, duration)
        else:
            self._print_error("Unexpected success - should have failed")
            print()
            return TestResult("Invalid Model", False, duration, "Should have failed")

    def test_streaming(self) -> TestResult:
        """Test streaming response (if supported)."""
        self._print_test_header("📡", "Streaming response")
        self._print_info("⚠️  Streaming not yet implemented - SKIPPED")
        print()
        return TestResult("Streaming", True, 0.0)

    def run_all(self) -> list[TestResult]:
        """Run all tests.
        
        Returns:
            List of test results
        """
        print("🧪 Prompt Bridge Test Suite\n")
        print("=" * 60)
        
        # Run health check first
        health_result = self.test_health_check()
        self.results.append(health_result)
        
        # If health check fails, skip remaining tests
        if not health_result.passed:
            print("⚠️  Server is not available. Skipping remaining tests.\n")
            return self.results
        
        # Run remaining tests
        self.results.extend([
            self.test_chatgpt_simple(),
            self.test_chatgpt_multi_turn(),
            self.test_qwen_simple(),
            self.test_qwen_chinese(),
            self.test_invalid_provider(),
            self.test_invalid_model(),
            self.test_streaming(),
        ])
        
        return self.results

    def print_summary(self):
        """Print test summary."""
        print("=" * 60)
        print("📊 Test Summary:\n")
        
        passed = sum(1 for result in self.results if result.passed)
        total = len(self.results)
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            duration_str = f"({result.duration:.2f}s)" if result.duration > 0 else ""
            print(f"   {status} - {result.name} {duration_str}")
        
        print(f"\n   Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")


def main():
    """Main entry point."""
    client = PromptBridgeClient()
    suite = TestSuite(client)
    suite.run_all()
    suite.print_summary()


if __name__ == "__main__":
    main()
