#!/usr/bin/env python3
"""Detailed schema inspector that shows ALL attributes in every metric."""

import json
from collections import defaultdict
from src.devai_analytics.telemetry.receiver import OTLPReceiver
from src.devai_analytics.logging_config import setup_logging
import signal

class DetailedSchemaInspector:
    """Inspects every single attribute in Claude Code telemetry."""
    
    def __init__(self):
        self.event_count = 0
        self.all_metrics = []
        self.attribute_values = defaultdict(set)
        
    def inspect_metrics(self, request):
        """Deep inspection of all metric attributes."""
        self.event_count += 1
        
        for resource_metric in request.resource_metrics:
            resource_attrs = {}
            for attr in resource_metric.resource.attributes:
                resource_attrs[attr.key] = self._get_value(attr.value)
            
            for scope_metric in resource_metric.scope_metrics:
                scope_name = scope_metric.scope.name if scope_metric.scope else "unknown"
                
                for metric in scope_metric.metrics:
                    print(f"\n{'='*100}")
                    print(f"EVENT #{self.event_count} - METRIC: {metric.name}")
                    print(f"{'='*100}")
                    
                    print(f"📋 RESOURCE ATTRIBUTES:")
                    for key, value in resource_attrs.items():
                        print(f"  {key}: {value}")
                    
                    print(f"\n🎯 SCOPE: {scope_name}")
                    print(f"📊 DESCRIPTION: {metric.description}")
                    print(f"📏 UNIT: {metric.unit}")
                    
                    # Handle different metric types
                    data_points = []
                    if metric.HasField('gauge'):
                        print(f"🔢 TYPE: Gauge")
                        data_points = metric.gauge.data_points
                    elif metric.HasField('sum'):
                        print(f"🔢 TYPE: Sum")
                        print(f"   Monotonic: {metric.sum.is_monotonic}")
                        print(f"   Aggregation: {metric.sum.aggregation_temporality}")
                        data_points = metric.sum.data_points
                    elif metric.HasField('histogram'):
                        print(f"🔢 TYPE: Histogram")
                        data_points = metric.histogram.data_points
                    
                    print(f"\n📈 DATA POINTS ({len(data_points)}):")
                    
                    for i, dp in enumerate(data_points):
                        print(f"\n  🔍 DATA POINT {i+1}:")
                        print(f"    Start Time: {dp.start_time_unix_nano}")
                        print(f"    Time: {dp.time_unix_nano}")
                        
                        # Value
                        if dp.HasField('as_double'):
                            print(f"    Value: {dp.as_double} (double)")
                        elif dp.HasField('as_int'):
                            print(f"    Value: {dp.as_int} (int)")
                        
                        # Histogram specific
                        if metric.HasField('histogram'):
                            print(f"    Count: {dp.count}")
                            print(f"    Sum: {dp.sum}")
                            print(f"    Buckets: {list(dp.bucket_counts)}")
                            print(f"    Bounds: {list(dp.explicit_bounds)}")
                        
                        # MOST IMPORTANT: All attributes
                        print(f"    🏷️  ATTRIBUTES:")
                        dp_attrs = {}
                        for attr in dp.attributes:
                            attr_name = attr.key
                            attr_value = self._get_value(attr.value)
                            dp_attrs[attr_name] = attr_value
                            self.attribute_values[f"{metric.name}.{attr_name}"].add(str(attr_value))
                            print(f"      {attr_name}: {attr_value} ({type(attr_value).__name__})")
                        
                        # Store for analysis
                        self.all_metrics.append({
                            'metric_name': metric.name,
                            'description': metric.description,
                            'unit': metric.unit,
                            'scope': scope_name,
                            'resource_attributes': resource_attrs,
                            'data_point_attributes': dp_attrs,
                            'value': dp.as_double if dp.HasField('as_double') else (dp.as_int if dp.HasField('as_int') else None),
                            'timestamp': dp.time_unix_nano
                        })
    
    def _get_value(self, any_value):
        """Extract value from AnyValue."""
        if any_value.HasField('string_value'):
            return any_value.string_value
        elif any_value.HasField('int_value'):
            return any_value.int_value
        elif any_value.HasField('double_value'):
            return any_value.double_value
        elif any_value.HasField('bool_value'):
            return any_value.bool_value
        elif any_value.HasField('array_value'):
            return [self._get_value(v) for v in any_value.array_value.values]
        elif any_value.HasField('kvlist_value'):
            return {kv.key: self._get_value(kv.value) for kv in any_value.kvlist_value.values}
        elif any_value.HasField('bytes_value'):
            return any_value.bytes_value.hex()
        return "unknown"
    
    def print_analysis(self):
        """Print comprehensive analysis of all discovered data."""
        print(f"\n{'='*100}")
        print("COMPREHENSIVE CLAUDE CODE TELEMETRY ANALYSIS")
        print(f"{'='*100}")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total Events Captured: {len(self.all_metrics)}")
        
        # Group by metric name
        metrics_by_name = defaultdict(list)
        for metric in self.all_metrics:
            metrics_by_name[metric['metric_name']].append(metric)
        
        print(f"  Unique Metrics: {len(metrics_by_name)}")
        
        for metric_name, events in metrics_by_name.items():
            print(f"\n🔍 {metric_name} ({len(events)} events)")
            first_event = events[0]
            print(f"  Description: {first_event['description']}")
            print(f"  Unit: {first_event['unit']}")
            
            # Show all unique attribute values
            all_attrs = set()
            for event in events:
                all_attrs.update(event['data_point_attributes'].keys())
            
            print(f"  Data Point Attributes: {', '.join(sorted(all_attrs))}")
            
            # Show attribute value ranges
            for attr in sorted(all_attrs):
                unique_values = self.attribute_values.get(f"{metric_name}.{attr}", set())
                if len(unique_values) <= 10:
                    print(f"    {attr}: {', '.join(sorted(unique_values))}")
                else:
                    sample_values = list(sorted(unique_values))[:5]
                    print(f"    {attr}: {', '.join(sample_values)} ... (+{len(unique_values)-5} more)")
        
        print(f"\n💎 POTENTIALLY MISSING DATA:")
        expected_metrics = {
            'claude_code.lines_modified',
            'claude_code.pull_request.created',
            'claude_code.commit.created', 
            'claude_code.tool_permission.decision',
            'claude_code.api_request.duration',
            'claude_code.tool_execution.duration'
        }
        
        found_metrics = set(metrics_by_name.keys())
        missing_metrics = expected_metrics - found_metrics
        
        if missing_metrics:
            print(f"  Expected but not seen: {', '.join(missing_metrics)}")
            print(f"  Note: These might require specific actions or different config")
        else:
            print(f"  All expected metric types have been observed!")
        
        print(f"\n🎯 EXTRACTION COMPLETENESS:")
        print(f"  We are capturing ALL available attributes from Claude Code telemetry!")
        print(f"  Total unique attribute patterns: {len(self.attribute_values)}")
        
        # Show which attributes have the most variety
        print(f"\n📈 MOST DYNAMIC ATTRIBUTES:")
        sorted_attrs = sorted(self.attribute_values.items(), key=lambda x: len(x[1]), reverse=True)
        for attr_name, values in sorted_attrs[:10]:
            print(f"  {attr_name}: {len(values)} unique values")

def main():
    """Run detailed schema inspection."""
    setup_logging("WARNING")
    
    inspector = DetailedSchemaInspector()
    receiver = OTLPReceiver()
    
    receiver.set_metrics_processor(inspector.inspect_metrics)
    
    print("🔬 DETAILED CLAUDE CODE TELEMETRY SCHEMA INSPECTOR")
    print("=" * 100)
    print("This will show EVERY attribute in EVERY metric with all possible values")
    print("Perform various actions in Claude Code:")
    print("- Ask questions")
    print("- Edit files") 
    print("- Run commands")
    print("- Use tools")
    print("- Create commits/PRs (if possible)")
    print("Press Ctrl+C when done to see the complete analysis")
    print()
    
    def signal_handler(signum, frame):
        print(f"\n\n🔬 Analysis complete!")
        inspector.print_analysis()
        receiver.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        receiver.start()
        receiver.wait_for_termination()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()