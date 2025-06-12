"""OpenTelemetry OTLP/gRPC receiver for Claude Code telemetry data."""

import logging
from typing import Any, Dict, List, Optional
from concurrent import futures
import grpc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2_grpc
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2_grpc
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
    ExportLogsServiceResponse,
)
from ..logging_config import ReceiverError, handle_telemetry_error

logger = logging.getLogger(__name__)


class MetricsServicer(metrics_service_pb2_grpc.MetricsServiceServicer):
    """gRPC servicer for receiving OpenTelemetry metrics."""
    
    def __init__(self, processor_callback=None):
        self.processor_callback = processor_callback
    
    def Export(self, request: ExportMetricsServiceRequest, context) -> ExportMetricsServiceResponse:
        """Handle incoming metrics data from Claude Code."""
        try:
            logger.info(f"Received metrics export with {len(request.resource_metrics)} resource metrics")
            
            if self.processor_callback:
                self.processor_callback(request)
            
            return ExportMetricsServiceResponse()
        except Exception as e:
            logger.error(f"Error processing metrics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Processing error: {str(e)}")
            return ExportMetricsServiceResponse()


class TraceServicer(trace_service_pb2_grpc.TraceServiceServicer):
    """gRPC servicer for receiving OpenTelemetry traces."""
    
    def __init__(self, processor_callback=None):
        self.processor_callback = processor_callback
    
    def Export(self, request: ExportTraceServiceRequest, context) -> ExportTraceServiceResponse:
        """Handle incoming trace data from Claude Code."""
        try:
            logger.info(f"Received trace export with {len(request.resource_spans)} resource spans")
            
            if self.processor_callback:
                self.processor_callback(request)
            
            return ExportTraceServiceResponse()
        except Exception as e:
            logger.error(f"Error processing traces: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Processing error: {str(e)}")
            return ExportTraceServiceResponse()


class LogsServicer(logs_service_pb2_grpc.LogsServiceServicer):
    """gRPC servicer for receiving OpenTelemetry logs."""
    
    def __init__(self, processor_callback=None):
        self.processor_callback = processor_callback
    
    def Export(self, request: ExportLogsServiceRequest, context) -> ExportLogsServiceResponse:
        """Handle incoming logs data from Claude Code."""
        try:
            logger.info(f"Received logs export with {len(request.resource_logs)} resource logs")
            
            if self.processor_callback:
                self.processor_callback(request)
            
            return ExportLogsServiceResponse()
        except Exception as e:
            logger.error(f"Error processing logs: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Processing error: {str(e)}")
            return ExportLogsServiceResponse()


class OTLPReceiver:
    """OTLP/gRPC receiver for Claude Code telemetry."""
    
    def __init__(self, host: str = "localhost", port: int = 4317):
        self.host = host
        self.port = port
        self.server: Optional[grpc.Server] = None
        self.metrics_processor = None
        self.trace_processor = None
        self.logs_processor = None
    
    def set_metrics_processor(self, callback):
        """Set callback function to process received metrics."""
        self.metrics_processor = callback
    
    def set_trace_processor(self, callback):
        """Set callback function to process received traces."""
        self.trace_processor = callback
    
    def set_logs_processor(self, callback):
        """Set callback function to process received logs."""
        self.logs_processor = callback
    
    @handle_telemetry_error
    def start(self):
        """Start the OTLP gRPC server."""
        try:
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            
            # Add servicers
            metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(
                MetricsServicer(self.metrics_processor),
                self.server
            )
            trace_service_pb2_grpc.add_TraceServiceServicer_to_server(
                TraceServicer(self.trace_processor),
                self.server
            )
            logs_service_pb2_grpc.add_LogsServiceServicer_to_server(
                LogsServicer(self.logs_processor),
                self.server
            )
            
            listen_addr = f"{self.host}:{self.port}"
            self.server.add_insecure_port(listen_addr)
            self.server.start()
            
            logger.info(f"OTLP receiver started on {listen_addr}")
            return self.server
            
        except Exception as e:
            logger.error(f"Failed to start OTLP receiver: {e}")
            raise ReceiverError(f"Failed to start receiver on {self.host}:{self.port}") from e
    
    def stop(self, grace_period: float = 5.0):
        """Stop the OTLP gRPC server."""
        if self.server:
            logger.info("Stopping OTLP receiver...")
            self.server.stop(grace_period)
            self.server = None
    
    def wait_for_termination(self):
        """Block until the server terminates."""
        if self.server:
            self.server.wait_for_termination()