from datetime import datetime, timezone
import logging
from typing import List, Dict, Any
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

logger = logging.getLogger("agentwatch.otlp")

def extract_otel_value(value_proto) -> Any:
    """Helper to extract native python values from OTel AnyValue protobuf messages."""
    if value_proto.HasField("string_value"):
        return value_proto.string_value
    elif value_proto.HasField("int_value"):
        return value_proto.int_value
    elif value_proto.HasField("double_value"):
        return value_proto.double_value
    elif value_proto.HasField("bool_value"):
        return value_proto.bool_value
    elif value_proto.HasField("array_value"):
        return [extract_otel_value(v) for v in value_proto.array_value.values]
    elif value_proto.HasField("kvlist_value"):
        return {kv.key: extract_otel_value(kv.value) for kv in value_proto.kvlist_value.values}
    return None

def decode_otlp_request(body: bytes) -> List[Dict[str, Any]]:
    """Decode OTLP protobuf request and map to AgentWatch spans format."""
    request = ExportTraceServiceRequest()
    try:
        request.ParseFromString(body)
    except Exception as e:
        logger.error(f"Failed to parse OTLP ExportTraceServiceRequest protobuf: {e}")
        return []
        
    spans = []
    for resource_span in request.resource_spans:
        # Resource-level attributes (e.g. service.name)
        resource_attributes = {}
        for attr in resource_span.resource.attributes:
            resource_attributes[attr.key] = extract_otel_value(attr.value)
            
        for scope_span in resource_span.scope_spans:
            for otel_span in scope_span.spans:
                # Basic span details
                span_dict = {
                    "span_id": otel_span.span_id.hex(),
                    "run_id": otel_span.trace_id.hex(),
                    "parent_span_id": otel_span.parent_span_id.hex() if otel_span.parent_span_id else None,
                    "span_type": "llm",  # Default to llm for GenAI semconv
                    "name": otel_span.name,
                    # Convert nanoseconds to timezone-aware datetime
                    "started_at": datetime.fromtimestamp(otel_span.start_time_unix_nano / 1e9, tz=timezone.utc),
                    "ended_at": datetime.fromtimestamp(otel_span.end_time_unix_nano / 1e9, tz=timezone.utc) if otel_span.end_time_unix_nano else None,
                    "status": "success" if otel_span.status.code in (0, 1) else "error",
                    "error_message": otel_span.status.message if otel_span.status.message else None,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "metadata": {
                        "source": "otel",
                        "otel.kind": otel_span.kind,
                        **resource_attributes
                    }
                }
                
                # Extract and map all OTel attributes
                for attr in otel_span.attributes:
                    key = attr.key
                    val = extract_otel_value(attr.value)
                    
                    if key == "gen_ai.usage.input_tokens":
                        span_dict["prompt_tokens"] = int(val)
                    elif key == "gen_ai.usage.output_tokens":
                        span_dict["completion_tokens"] = int(val)
                    elif key == "gen_ai.system":
                        span_dict["provider"] = str(val)
                    elif key == "gen_ai.request.model":
                        span_dict["model"] = str(val)
                    elif key == "span.type":
                        # Custom span type override if specified
                        span_dict["span_type"] = str(val)
                    else:
                        # Store all other custom attributes inside metadata
                        span_dict["metadata"][key] = val
                        
                spans.append(span_dict)
                
    return spans
