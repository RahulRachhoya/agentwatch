from opentelemetry.proto.trace.v1.trace_pb2 import TracesData
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from datetime import datetime

def decode_otlp_request(body: bytes) -> list:
    """Decode OTLP protobuf and map to AgentWatch spans."""
    request = ExportTraceServiceRequest()
    request.ParseFromString(body)
    
    spans = []
    for resource_span in request.resource_spans:
        for scope_span in resource_span.scope_spans:
            for otel_span in scope_span.spans:
                # Map OTel span to AgentWatch span
                span_dict = {
                    "span_id": otel_span.span_id.hex(),
                    "run_id": otel_span.trace_id.hex(),
                    "parent_span_id": otel_span.parent_span_id.hex() if otel_span.parent_span_id else None,
                    "span_type": "llm",  # default
                    "name": otel_span.name,
                    "started_at": datetime.fromtimestamp(otel_span.start_time_unix_nano / 1e9).isoformat(),
                    "ended_at": datetime.fromtimestamp(otel_span.end_time_unix_nano / 1e9).isoformat() if otel_span.end_time_unix_nano else None,
                    "status": "success" if otel_span.status.code == 0 else "error",
                    "metadata": {"source": "otel"}
                }
                
                # Extract GenAI semantic convention attributes
                for attr in otel_span.attributes:
                    key = attr.key
                    if key == "gen_ai.usage.input_tokens":
                        span_dict["prompt_tokens"] = attr.value.int_value
                    elif key == "gen_ai.usage.output_tokens":
                        span_dict["completion_tokens"] = attr.value.int_value
                    elif key == "gen_ai.system":
                        span_dict["provider"] = attr.value.string_value
                    elif key == "gen_ai.request.model":
                        span_dict["model"] = attr.value.string_value
                
                spans.append(span_dict)
    
    return spans
