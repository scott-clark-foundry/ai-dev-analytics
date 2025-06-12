"""Metric processor for parsing Claude Code telemetry data."""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import KeyValue
from ..logging_config import ProcessorError, handle_telemetry_error

logger = logging.getLogger(__name__)


class TelemetryProcessor:
    """Processes OpenTelemetry data from Claude Code."""
    
    def __init__(self, storage_callback=None):
        self.storage_callback = storage_callback
    
    @handle_telemetry_error
    def process_metrics(self, request: ExportMetricsServiceRequest):
        """Process incoming metrics data."""
        try:
            logger.info(f"TelemetryProcessor.process_metrics called with {len(request.resource_metrics)} resource metrics")
            
            for resource_metric in request.resource_metrics:
                resource_attrs = self._extract_attributes(resource_metric.resource.attributes)
                logger.info(f"Processing resource with attributes: {resource_attrs}")
                
                for scope_metric in resource_metric.scope_metrics:
                    scope_name = scope_metric.scope.name if scope_metric.scope else "unknown"
                    logger.info(f"Processing scope: {scope_name}")
                    
                    for metric in scope_metric.metrics:
                        logger.info(f"Processing metric: {metric.name}")
                        processed_metric = self._process_metric(metric, resource_attrs, scope_name)
                        if processed_metric and self.storage_callback:
                            logger.info(f"Calling storage callback for metric: {metric.name}")
                            self.storage_callback('metric', processed_metric)
                        else:
                            logger.warning(f"No storage callback or processed metric is None for: {metric.name}")
                            
        except Exception as e:
            logger.error(f"Error processing metrics: {e}", exc_info=True)
            raise ProcessorError(f"Failed to process metrics") from e
    
    @handle_telemetry_error
    def process_traces(self, request: ExportTraceServiceRequest):
        """Process incoming trace data."""
        try:
            for resource_span in request.resource_spans:
                resource_attrs = self._extract_attributes(resource_span.resource.attributes)
                
                for scope_span in resource_span.scope_spans:
                    scope_name = scope_span.scope.name if scope_span.scope else "unknown"
                    
                    for span in scope_span.spans:
                        processed_span = self._process_span(span, resource_attrs, scope_name)
                        if processed_span and self.storage_callback:
                            self.storage_callback('trace', processed_span)
                            
        except Exception as e:
            logger.error(f"Error processing traces: {e}")
            raise ProcessorError(f"Failed to process traces") from e
    
    @handle_telemetry_error
    def process_logs(self, request: ExportLogsServiceRequest):
        """Process incoming logs data."""
        try:
            logger.info(f"TelemetryProcessor.process_logs called with {len(request.resource_logs)} resource logs")
            
            for resource_log in request.resource_logs:
                resource_attrs = self._extract_attributes(resource_log.resource.attributes)
                logger.info(f"Processing log resource with attributes: {resource_attrs}")
                
                for scope_log in resource_log.scope_logs:
                    scope_name = scope_log.scope.name if scope_log.scope else "unknown"
                    logger.info(f"Processing log scope: {scope_name}")
                    
                    for log_record in scope_log.log_records:
                        logger.info(f"Processing log record: {log_record.body}")
                        processed_log = self._process_log_record(log_record, resource_attrs, scope_name)
                        if processed_log and self.storage_callback:
                            # Extract session.id from log attributes if available
                            log_attrs = processed_log.get('attributes', {})
                            session_id = log_attrs.get('session.id')
                            if session_id:
                                processed_log['resource_attributes']['session.id'] = session_id
                            
                            logger.info(f"Calling storage callback for log")
                            self.storage_callback('log', processed_log)
                        else:
                            logger.warning(f"No storage callback or processed log is None")
                            
        except Exception as e:
            logger.error(f"Error processing logs: {e}", exc_info=True)
            raise ProcessorError(f"Failed to process logs") from e
    
    def _extract_attributes(self, attributes: List[KeyValue]) -> Dict[str, Any]:
        """Extract attributes from OpenTelemetry KeyValue list."""
        attrs = {}
        for attr in attributes:
            key = attr.key
            value = None
            
            if attr.value.HasField('string_value'):
                value = attr.value.string_value
            elif attr.value.HasField('int_value'):
                value = attr.value.int_value
            elif attr.value.HasField('double_value'):
                value = attr.value.double_value
            elif attr.value.HasField('bool_value'):
                value = attr.value.bool_value
            
            if value is not None:
                attrs[key] = value
                
        return attrs
    
    def _process_metric(self, metric, resource_attrs: Dict[str, Any], scope_name: str) -> Optional[Dict[str, Any]]:
        """Process a single metric."""
        try:
            processed = {
                'name': metric.name,
                'description': metric.description,
                'unit': metric.unit,
                'scope': scope_name,
                'resource_attributes': resource_attrs,
                'timestamp': datetime.utcnow().isoformat(),
                'data_points': []
            }
            
            # Handle different metric types
            if metric.HasField('gauge'):
                for dp in metric.gauge.data_points:
                    processed['data_points'].append(self._process_data_point(dp))
            elif metric.HasField('sum'):
                for dp in metric.sum.data_points:
                    processed['data_points'].append(self._process_data_point(dp))
            elif metric.HasField('histogram'):
                for dp in metric.histogram.data_points:
                    processed['data_points'].append(self._process_histogram_data_point(dp))
            
            # Extract session.id from the first data point if available
            if processed['data_points']:
                first_dp = processed['data_points'][0]
                session_id = first_dp.get('attributes', {}).get('session.id')
                if session_id:
                    # Add session.id to resource attributes for easier access
                    processed['resource_attributes']['session.id'] = session_id
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing metric {metric.name}: {e}")
            return None
    
    def _process_span(self, span, resource_attrs: Dict[str, Any], scope_name: str) -> Optional[Dict[str, Any]]:
        """Process a single trace span."""
        try:
            processed = {
                'trace_id': span.trace_id.hex(),
                'span_id': span.span_id.hex(),
                'parent_span_id': span.parent_span_id.hex() if span.parent_span_id else None,
                'name': span.name,
                'kind': span.kind,
                'start_time': self._nano_to_datetime(span.start_time_unix_nano),
                'end_time': self._nano_to_datetime(span.end_time_unix_nano),
                'duration_ms': (span.end_time_unix_nano - span.start_time_unix_nano) / 1_000_000,
                'attributes': self._extract_attributes(span.attributes),
                'resource_attributes': resource_attrs,
                'scope': scope_name,
                'status': {
                    'code': span.status.code,
                    'message': span.status.message
                }
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing span {span.name}: {e}")
            return None
    
    def _process_data_point(self, data_point) -> Dict[str, Any]:
        """Process a numeric data point."""
        dp = {
            'attributes': self._extract_attributes(data_point.attributes),
            'start_time': self._nano_to_datetime(data_point.start_time_unix_nano),
            'time': self._nano_to_datetime(data_point.time_unix_nano),
        }
        
        if data_point.HasField('as_double'):
            dp['value'] = data_point.as_double
        elif data_point.HasField('as_int'):
            dp['value'] = data_point.as_int
            
        return dp
    
    def _process_histogram_data_point(self, data_point) -> Dict[str, Any]:
        """Process a histogram data point."""
        return {
            'attributes': self._extract_attributes(data_point.attributes),
            'start_time': self._nano_to_datetime(data_point.start_time_unix_nano),
            'time': self._nano_to_datetime(data_point.time_unix_nano),
            'count': data_point.count,
            'sum': data_point.sum if data_point.HasField('sum') else None,
            'bucket_counts': list(data_point.bucket_counts),
            'explicit_bounds': list(data_point.explicit_bounds)
        }
    
    def _process_log_record(self, log_record, resource_attrs: Dict[str, Any], scope_name: str) -> Optional[Dict[str, Any]]:
        """Process a single log record."""
        try:
            processed = {
                'timestamp': self._nano_to_datetime(log_record.time_unix_nano),
                'observed_timestamp': self._nano_to_datetime(log_record.observed_time_unix_nano),
                'severity_number': log_record.severity_number,
                'severity_text': log_record.severity_text,
                'body': self._get_log_body(log_record.body),
                'attributes': self._extract_attributes(log_record.attributes),
                'resource_attributes': resource_attrs,
                'scope': scope_name,
                'trace_id': log_record.trace_id.hex() if log_record.trace_id else None,
                'span_id': log_record.span_id.hex() if log_record.span_id else None,
                'flags': log_record.flags
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing log record: {e}")
            return None
    
    def _get_log_body(self, body):
        """Extract log body content."""
        if body.HasField('string_value'):
            return body.string_value
        elif body.HasField('int_value'):
            return body.int_value
        elif body.HasField('double_value'):
            return body.double_value
        elif body.HasField('bool_value'):
            return body.bool_value
        elif body.HasField('bytes_value'):
            return body.bytes_value.hex()
        return str(body)
    
    def _nano_to_datetime(self, nano_timestamp: int) -> str:
        """Convert nanosecond timestamp to ISO datetime string."""
        if nano_timestamp == 0:
            return None
        return datetime.fromtimestamp(nano_timestamp / 1_000_000_000).isoformat()