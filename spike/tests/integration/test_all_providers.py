"""
Q5: Multi-Provider SDK Patch Validation

Tests all 5 providers with mocked responses:
1. Anthropic - native SDK
2. Bedrock Claude - boto3 with anthropic.claude extractor
3. Bedrock Llama - boto3 with meta.llama extractor
4. DeepSeek - OpenAI-compatible with base_url detection
5. Kimi/Moonshot - OpenAI-compatible with base_url detection
"""
import json
import time
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Import patches
import sys
sys.path.insert(0, 'sdk')
from patch_anthropic import install as install_anthropic
from patch_bedrock import install as install_bedrock, TOKEN_EXTRACTORS
from patch_openai_compat import install as install_openai_compat, _detect_provider


def test_anthropic_patch():
    """Test 1: Anthropic native SDK patch"""
    print("\n=== TEST 1: Anthropic Patch ===")

    # Mock Anthropic client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.usage.input_tokens = 15
    mock_response.usage.output_tokens = 25

    original_create = Mock(return_value=mock_response)
    mock_client.messages.create = original_create

    # Install patch
    with patch('sdk.patch_anthropic.httpx.post') as mock_post:
        install_anthropic(mock_client)

        # Call patched method
        response = mock_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )

        # Verify response
        assert response == mock_response
        assert response.usage.input_tokens == 15
        assert response.usage.output_tokens == 25

        # Verify span sent
        assert mock_post.called
        call_args = mock_post.call_args
        span_data = call_args[1]['json']['spans'][0]

        assert span_data['provider'] == 'anthropic'
        assert span_data['model'] == 'claude-3-5-sonnet-20241022'
        assert span_data['prompt_tokens'] == 15
        assert span_data['completion_tokens'] == 25

        print(f"[OK] Anthropic span sent: provider={span_data['provider']}, "
              f"tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")
        return span_data


def test_bedrock_claude_patch():
    """Test 2: Bedrock Claude with anthropic.claude extractor"""
    print("\n=== TEST 2: Bedrock Claude Patch ===")

    # Mock boto3 client
    mock_client = Mock()

    # Create realistic Claude response
    claude_response = {
        "id": "msg_123",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": "Hi!"}],
        "model": "claude-3-5-sonnet-20241022",
        "usage": {
            "input_tokens": 12,
            "output_tokens": 8
        }
    }

    # Create a mock body that behaves like StreamingBody
    class MockBody:
        def __init__(self, data):
            self.data = data
            self.pos = 0

        def read(self):
            if self.pos == 0:
                self.pos = 1
                return self.data.encode()
            return b''

    mock_body = MockBody(json.dumps(claude_response))
    mock_response = {"body": mock_body}
    original_invoke = Mock(return_value=mock_response)
    mock_client.invoke_model = original_invoke

    # Install patch
    with patch('sdk.patch_bedrock.httpx.post') as mock_post:
        install_bedrock(mock_client)

        # Call patched method
        response = mock_client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Say hi"}]
            })
        )

        # Verify extractor works
        body = json.loads(response["body"].read())
        assert body["usage"]["input_tokens"] == 12
        assert body["usage"]["output_tokens"] == 8

        # Verify span sent
        assert mock_post.called
        call_args = mock_post.call_args
        span_data = call_args[1]['json']['spans'][0]

        assert span_data['provider'] == 'bedrock'
        assert 'anthropic.claude' in span_data['model']
        assert span_data['prompt_tokens'] == 12
        assert span_data['completion_tokens'] == 8

        print(f"[OK] Bedrock Claude span sent: provider={span_data['provider']}, "
              f"model={span_data['model']}, tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")
        return span_data


def test_bedrock_llama_patch():
    """Test 3: Bedrock Llama with meta.llama extractor"""
    print("\n=== TEST 3: Bedrock Llama Patch ===")

    # Mock boto3 client
    mock_client = Mock()

    # Create realistic Llama response
    llama_response = {
        "generation": "Hello!",
        "prompt_token_count": 18,
        "generation_token_count": 6,
        "stop_reason": "stop"
    }

    # Create a mock body that behaves like StreamingBody
    class MockBody:
        def __init__(self, data):
            self.data = data
            self.pos = 0

        def read(self):
            if self.pos == 0:
                self.pos = 1
                return self.data.encode()
            return b''

    mock_body = MockBody(json.dumps(llama_response))
    mock_response = {"body": mock_body}
    original_invoke = Mock(return_value=mock_response)
    mock_client.invoke_model = original_invoke

    # Install patch
    with patch('sdk.patch_bedrock.httpx.post') as mock_post:
        install_bedrock(mock_client)

        # Call patched method
        response = mock_client.invoke_model(
            modelId="meta.llama3-1-70b-instruct-v1:0",
            body=json.dumps({
                "prompt": "Say hi",
                "max_gen_len": 10,
                "temperature": 0.7
            })
        )

        # Verify extractor works
        body = json.loads(response["body"].read())
        assert body["prompt_token_count"] == 18
        assert body["generation_token_count"] == 6

        # Verify span sent
        assert mock_post.called
        call_args = mock_post.call_args
        span_data = call_args[1]['json']['spans'][0]

        assert span_data['provider'] == 'bedrock'
        assert 'meta.llama' in span_data['model']
        assert span_data['prompt_tokens'] == 18
        assert span_data['completion_tokens'] == 6

        print(f"[OK] Bedrock Llama span sent: provider={span_data['provider']}, "
              f"model={span_data['model']}, tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")
        return span_data


def test_deepseek_patch():
    """Test 4: DeepSeek via OpenAI-compatible patch"""
    print("\n=== TEST 4: DeepSeek Patch ===")

    # Mock OpenAI client with DeepSeek base_url
    mock_client = Mock()
    mock_client.base_url = "https://api.deepseek.com"

    # Create realistic OpenAI-compatible response
    mock_usage = Mock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 15

    mock_response = Mock()
    mock_response.usage = mock_usage
    mock_response.model = "deepseek-chat"

    original_create = Mock(return_value=mock_response)
    mock_client.chat.completions.create = original_create

    # Install patch
    with patch('sdk.patch_openai_compat.httpx.post') as mock_post:
        install_openai_compat(mock_client)

        # Verify provider detection
        assert _detect_provider("https://api.deepseek.com") == "deepseek"

        # Call patched method
        response = mock_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10
        )

        # Verify response
        assert response == mock_response

        # Verify span sent
        assert mock_post.called
        call_args = mock_post.call_args
        span_data = call_args[1]['json']['spans'][0]

        assert span_data['provider'] == 'deepseek'
        assert span_data['model'] == 'deepseek-chat'
        assert span_data['prompt_tokens'] == 10
        assert span_data['completion_tokens'] == 15

        print(f"[OK] DeepSeek span sent: provider={span_data['provider']}, "
              f"model={span_data['model']}, tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")
        return span_data


def test_moonshot_patch():
    """Test 5: Moonshot/Kimi via OpenAI-compatible patch"""
    print("\n=== TEST 5: Moonshot/Kimi Patch ===")

    # Mock OpenAI client with Moonshot base_url
    mock_client = Mock()
    mock_client.base_url = "https://api.moonshot.cn/v1"

    # Create realistic OpenAI-compatible response
    mock_usage = Mock()
    mock_usage.prompt_tokens = 14
    mock_usage.completion_tokens = 9

    mock_response = Mock()
    mock_response.usage = mock_usage
    mock_response.model = "moonshot-v1-8k"

    original_create = Mock(return_value=mock_response)
    mock_client.chat.completions.create = original_create

    # Install patch
    with patch('sdk.patch_openai_compat.httpx.post') as mock_post:
        install_openai_compat(mock_client)

        # Verify provider detection
        assert _detect_provider("https://api.moonshot.cn/v1") == "moonshot"

        # Call patched method
        response = mock_client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10
        )

        # Verify response
        assert response == mock_response

        # Verify span sent
        assert mock_post.called
        call_args = mock_post.call_args
        span_data = call_args[1]['json']['spans'][0]

        assert span_data['provider'] == 'moonshot'
        assert span_data['model'] == 'moonshot-v1-8k'
        assert span_data['prompt_tokens'] == 14
        assert span_data['completion_tokens'] == 9

        print(f"[OK] Moonshot span sent: provider={span_data['provider']}, "
              f"model={span_data['model']}, tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")
        return span_data


def test_token_extractors():
    """Verify TOKEN_EXTRACTORS registry"""
    print("\n=== TOKEN_EXTRACTORS Registry ===")

    # Test Claude extractor
    claude_body = {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }
    claude_tokens = TOKEN_EXTRACTORS["anthropic.claude"](claude_body)
    assert claude_tokens["prompt_tokens"] == 100
    assert claude_tokens["completion_tokens"] == 50
    print("[OK] anthropic.claude extractor works")

    # Test Llama extractor
    llama_body = {
        "prompt_token_count": 75,
        "generation_token_count": 25
    }
    llama_tokens = TOKEN_EXTRACTORS["meta.llama"](llama_body)
    assert llama_tokens["prompt_tokens"] == 75
    assert llama_tokens["completion_tokens"] == 25
    print("[OK] meta.llama extractor works")

    # Test Titan extractor
    titan_body = {
        "inputTextTokenCount": 60,
        "results": [{"tokenCount": 40}]
    }
    titan_tokens = TOKEN_EXTRACTORS["amazon.titan"](titan_body)
    assert titan_tokens["prompt_tokens"] == 60
    assert titan_tokens["completion_tokens"] == 40
    print("[OK] amazon.titan extractor works")


def run_all_tests():
    """Run all provider tests"""
    print("=" * 70)
    print("Q5: Multi-Provider SDK Patch Validation")
    print("=" * 70)

    results = []

    try:
        # Test token extractors
        test_token_extractors()

        # Test each provider
        results.append(("Anthropic", test_anthropic_patch()))
        results.append(("Bedrock Claude", test_bedrock_claude_patch()))
        results.append(("Bedrock Llama", test_bedrock_llama_patch()))
        results.append(("DeepSeek", test_deepseek_patch()))
        results.append(("Moonshot", test_moonshot_patch()))

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        for provider, span_data in results:
            print(f"[OK] {provider:20} -> provider={span_data['provider']:12} "
                  f"tokens={span_data['prompt_tokens']}/{span_data['completion_tokens']}")

        print(f"\nPASS: All 5 providers emit spans with correct provider field and token extraction")
        return True

    except Exception as e:
        print(f"\n[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
