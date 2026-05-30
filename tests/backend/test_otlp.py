"""
Test suite for OTLP protobuf decoding.

Tests protobuf parsing, semantic conventions extraction, and span mapping.
"""
import pytest
from datetime import datetime, timezone
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue

from backend.otlp import extract_otel_value, decode_otlp_request


class TestExtractOtelValue:
    """Test OTel AnyValue extraction."""

    def test_extract_string_value(self):
        """Should extract string values."""
        value = AnyValue(string_value="test_string")
        result = extract_otel_value(value)
        assert result == "test_string"

    def test_extract_int_value(self):
        """Should extract integer values."""
        value = AnyValue(int_value=42)
        result = extract_otel_value(value)
        assert result == 42

    def test_extract_double_value(self):
        """Should extract double/float values."""
        value = AnyValue(double_value=3.14)
        result = extract_otel_value(value)
        assert result == 3.14

    def test_extract_bool_value(self):
        """Should extract boolean values."""
        value_true = AnyValue(bool_value=True)
        value_false = AnyValue(bool_value=False)
        assert extract_otel_value(value_true) is True
        assert extract_otel_value(value_false) is False

    def test_extract_array_value(self):
        """Should extract array values recursively."""
        array = AnyValue()
        array.array_value.values.append(AnyValue(string_value="item1"))
        array.array_value.values.append(AnyValue(int_value=123))

        result = extract_otel_value(array)
        assert result == ["item1", 123]

    def test_extract_kvlist_value(self):
        """Should extract key-value list as dictionary."""
        kvlist = AnyValue()
        kvlist.kvlist_value.values.append(
            KeyValue(key="name", value=AnyValue(string_value="Alice"))
        )
        kvlist.kvlist_value.values.append(
            KeyValue(key="age", value=AnyValue(int_value=30))
        )

        result = extract_otel_value(kvlist)
        assert result == {"name": "Alice", "age": 30}

    def test_extract_none_for_empty_value(self):
        """Should return None for empty AnyValue."""
        value = AnyValue()
        result = extract_otel_value(value)
        assert result is None


class TestDecodeOtlpRequest:
    """Test OTLP request decoding."""

    def test_decode_empty_request(self):
        """Should return empty list for empty request."""
        request = ExportTraceServiceRequest()
        spans = decode_otlp_request(request.SerializeToString())
        assert spans == []

    def test_decode_invalid_protobuf(self):
        """Should handle invalid protobuf gracefully."""
        invalid_data = b"not-a-valid-protobuf"
        spans = decode_otlp_request(invalid_data)
        assert spans == []

    def test_decode_single_span_basic(self):
        """Should decode a basic span with minimal attributes."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()

        # Add resource attributes
        resource_span.resource.attributes.append(
            KeyValue(key="service.name", value=AnyValue(string_value="test-service"))
        )

        # Add scope spans
        scope_span = resource_span.scope_spans.add()

        # Add a span
        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "test-span"
        span.start_time_unix_nano = 1717000000000000000
        span.end_time_unix_nano = 1717000005000000000
        span.status.code = Status.STATUS_CODE_OK

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert len(decoded_spans) == 1
        assert decoded_spans[0]["span_id"] == "0102030405060708"
        assert decoded_spans[0]["name"] == "test-span"
        assert decoded_spans[0]["span_type"] == "llm"  # default
        assert decoded_spans[0]["status"] == "success"

    def test_decode_span_with_parent(self):
        """Should decode parent span relationship."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.parent_span_id = b"\x11\x12\x13\x14\x15\x16\x17\x18"
        span.name = "child-span"
        span.start_time_unix_nano = 1717000000000000000

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["parent_span_id"] == "1112131415161718"

    def test_decode_span_with_genai_tokens(self):
        """Should extract gen_ai token usage attributes."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "llm-call"
        span.start_time_unix_nano = 1717000000000000000

        # Add gen_ai attributes
        span.attributes.append(
            KeyValue(key="gen_ai.usage.input_tokens", value=AnyValue(int_value=100))
        )
        span.attributes.append(
            KeyValue(key="gen_ai.usage.output_tokens", value=AnyValue(int_value=50))
        )
        span.attributes.append(
            KeyValue(key="gen_ai.system", value=AnyValue(string_value="openai"))
        )
        span.attributes.append(
            KeyValue(key="gen_ai.request.model", value=AnyValue(string_value="gpt-4o"))
        )

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["prompt_tokens"] == 100
        assert decoded_spans[0]["completion_tokens"] == 50
        assert decoded_spans[0]["provider"] == "openai"
        assert decoded_spans[0]["model"] == "gpt-4o"

    def test_decode_span_with_custom_type(self):
        """Should respect custom span.type attribute."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "tool-call"
        span.start_time_unix_nano = 1717000000000000000

        span.attributes.append(
            KeyValue(key="span.type", value=AnyValue(string_value="tool"))
        )

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["span_type"] == "tool"

    def test_decode_span_with_error_status(self):
        """Should map error status correctly."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "failed-span"
        span.start_time_unix_nano = 1717000000000000000
        span.status.code = Status.STATUS_CODE_ERROR
        span.status.message = "Connection timeout"

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["status"] == "error"
        assert decoded_spans[0]["error_message"] == "Connection timeout"

    def test_decode_span_with_custom_metadata(self):
        """Should preserve custom attributes in metadata."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "custom-span"
        span.start_time_unix_nano = 1717000000000000000

        span.attributes.append(
            KeyValue(key="custom.attribute", value=AnyValue(string_value="custom_value"))
        )

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["metadata"]["custom.attribute"] == "custom_value"
        assert decoded_spans[0]["metadata"]["source"] == "otel"

    def test_decode_multiple_spans(self):
        """Should decode multiple spans in a single request."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        # Add first span
        span1 = scope_span.spans.add()
        span1.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span1.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span1.name = "span-1"
        span1.start_time_unix_nano = 1717000000000000000

        # Add second span
        span2 = scope_span.spans.add()
        span2.span_id = b"\x11\x12\x13\x14\x15\x16\x17\x18"
        span2.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span2.name = "span-2"
        span2.start_time_unix_nano = 1717000001000000000

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert len(decoded_spans) == 2
        assert decoded_spans[0]["name"] == "span-1"
        assert decoded_spans[1]["name"] == "span-2"

    def test_decode_span_with_resource_attributes(self):
        """Should include resource attributes in metadata."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()

        # Add resource attributes
        resource_span.resource.attributes.append(
            KeyValue(key="service.name", value=AnyValue(string_value="my-service"))
        )
        resource_span.resource.attributes.append(
            KeyValue(key="service.version", value=AnyValue(string_value="1.0.0"))
        )

        scope_span = resource_span.scope_spans.add()
        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "test"
        span.start_time_unix_nano = 1717000000000000000

        decoded_spans = decode_otlp_request(request.SerializeToString())

        metadata = decoded_spans[0]["metadata"]
        assert metadata["service.name"] == "my-service"
        assert metadata["service.version"] == "1.0.0"

    def test_decode_span_timestamp_conversion(self):
        """Should convert nanosecond timestamps to datetime objects."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "test"
        span.start_time_unix_nano = 1717000000000000000  # nanoseconds
        span.end_time_unix_nano = 1717000005000000000

        decoded_spans = decode_otlp_request(request.SerializeToString())

        started_at = decoded_spans[0]["started_at"]
        ended_at = decoded_spans[0]["ended_at"]

        # Should be datetime objects with timezone
        assert isinstance(started_at, datetime)
        assert isinstance(ended_at, datetime)
        assert started_at.tzinfo == timezone.utc
        assert ended_at.tzinfo == timezone.utc

        # Verify conversion accuracy (5 second difference)
        duration = (ended_at - started_at).total_seconds()
        assert duration == 5.0

    def test_decode_span_without_end_time(self):
        """Should handle spans without end time."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "running-span"
        span.start_time_unix_nano = 1717000000000000000
        # No end_time_unix_nano set

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["ended_at"] is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_decode_span_with_null_parent(self):
        """Should handle null parent span ID gracefully."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "root-span"
        span.start_time_unix_nano = 1717000000000000000
        # No parent_span_id set

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["parent_span_id"] is None

    def test_decode_span_with_zero_tokens(self):
        """Should handle zero token usage."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "zero-tokens"
        span.start_time_unix_nano = 1717000000000000000

        span.attributes.append(
            KeyValue(key="gen_ai.usage.input_tokens", value=AnyValue(int_value=0))
        )
        span.attributes.append(
            KeyValue(key="gen_ai.usage.output_tokens", value=AnyValue(int_value=0))
        )

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["prompt_tokens"] == 0
        assert decoded_spans[0]["completion_tokens"] == 0

    def test_decode_span_with_unset_status(self):
        """Should default to success for unset status."""
        request = ExportTraceServiceRequest()
        resource_span = request.resource_spans.add()
        scope_span = resource_span.scope_spans.add()

        span = scope_span.spans.add()
        span.span_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        span.trace_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        span.name = "unset-status"
        span.start_time_unix_nano = 1717000000000000000
        # status code defaults to UNSET (0)

        decoded_spans = decode_otlp_request(request.SerializeToString())

        assert decoded_spans[0]["status"] == "success"
