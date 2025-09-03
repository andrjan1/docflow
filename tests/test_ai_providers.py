from unittest.mock import MagicMock
from docflow.ai.providers.openai import OpenAIProvider
import requests

class MockRequestsResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP Error {self.status_code}")

def mock_requests_get(url, *args, **kwargs):
    return MockRequestsResponse(b"dummy image bytes")

class MockOpenAIImage:
    def __init__(self, url):
        self.url = url

class MockOpenAIResponse:
    def __init__(self, url):
        self.data = [MockOpenAIImage(url)]

class MockOpenAIClient:
    def __init__(self, *args, **kwargs):
        self.images = MagicMock()
        self.images.generate.return_value = MockOpenAIResponse("http://fake-url.com/image.png")

def test_generate_image_success(monkeypatch):
    """
    Tests the successful generation of an image.
    """
    monkeypatch.setattr("docflow.ai.providers.openai.OpenAI", MockOpenAIClient)
    monkeypatch.setattr(requests, "get", mock_requests_get)

    provider = OpenAIProvider(api_key="fake_key")
    result = provider.generate_image("a test prompt")

    assert "image_bytes" in result
    assert result["image_bytes"] == b"dummy image bytes"
    assert "meta" in result
    assert result["meta"]["provider"] == "openai"
    assert result["meta"]["model"] == "dall-e-3"
    assert "error" not in result["meta"]

def test_generate_image_api_error(monkeypatch):
    """
    Tests the handling of an API error during image generation.
    """
    mock_client = MockOpenAIClient()
    mock_client.images.generate.side_effect = Exception("API Error")
    monkeypatch.setattr("docflow.ai.providers.openai.OpenAI", lambda *args, **kwargs: mock_client)

    provider = OpenAIProvider(api_key="fake_key")
    result = provider.generate_image("a test prompt")

    assert "image_bytes" in result
    assert result["image_bytes"] == b""
    assert "meta" in result
    assert "error" in result["meta"]
    assert result["meta"]["error"] == "API Error"

def test_generate_image_download_error(monkeypatch):
    """
    Tests the handling of a download error.
    """
    def mock_requests_get_error(*args, **kwargs):
        raise requests.exceptions.RequestException("Download Failed")

    monkeypatch.setattr("docflow.ai.providers.openai.OpenAI", MockOpenAIClient)
    monkeypatch.setattr(requests, "get", mock_requests_get_error)

    provider = OpenAIProvider(api_key="fake_key")
    result = provider.generate_image("a test prompt")

    assert "image_bytes" in result
    assert result["image_bytes"] == b""
    assert "meta" in result
    assert "error" in result["meta"]
    assert "Failed to download image" in result["meta"]["error"]
