"""
OpenTelemetry test trace emitter.

Emits a test trace with GenAI semantic conventions to /v1/traces (Q6 validation).
Uses opentelemetry-sdk to construct ExportTraceServiceRequest protobuf.
"""
import os
import time
import httpx
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

AGENTWATCH_URL = os.getenv("AGENTWATCH_URL", "http://localhost:8000")

def emit_test_trace():
    """Emit a test OTel trace with GenAI attributes."""
    # Configure OTLP exporter to target AgentWatch
    exporter = OTLPSpanExporter(
        endpoint=f"{AGENTWATCH_URL}/v1/traces",
        headers={}
    )
    
    provider = TracerProvider()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    tracer = trace.get_tracer(__name__)
    
    # Create parent span
    with tracer.start_as_current_span("agent.run") as parent_span:
        parent_span.set_attribute("service.name", "agentwatch-spike")
        parent_span.set_attribute("run.id", "otel-test-run")
        
        # Create child LLM span with GenAI semconv
        with tracer.start_as_current_span("llm.call") as llm_span:
            llm_span.set_attribute("gen_ai.system", "openai")
            llm_span.set_attribute("gen_ai.request.model", "gpt-4o-mini")
            llm_span.set_attribute("gen_ai.usage.input_tokens", 15)
            llm_span.set_attribute("gen_ai.usage.output_tokens", 8)
            llm_span.set_attribute("gen_ai.response.finish_reasons", ["stop"])
            
            time.sleep(0.1)  # Simulate LLM call
    
    # Force export
    provider.force_flush()
    print("OTel trace emitted to", f"{AGENTWATCH_URL}/v1/traces")

if __name__ == "__main__":
    emit_test_trace()
