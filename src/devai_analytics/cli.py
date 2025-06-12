"""Command-line interface for the AI Development Analytics telemetry collector."""

import argparse
import asyncio
import logging
import signal
import sys
import time
from typing import Optional
from .telemetry.receiver import OTLPReceiver
from .telemetry.processor import TelemetryProcessor
from .storage import InMemoryStorage
from .display import RealTimeDisplay, print_welcome, print_startup_info
from .sample_data import SampleDataGenerator
from .logging_config import setup_logging


class TelemetryCollector:
    """Main telemetry collector application."""
    
    def __init__(self, host: str = "localhost", port: int = 4317, demo_mode: bool = False):
        self.host = host
        self.port = port
        self.demo_mode = demo_mode
        self.running = False
        
        # Components
        self.storage = InMemoryStorage()
        self.processor = TelemetryProcessor(storage_callback=self.storage.store_event)
        self.receiver = OTLPReceiver(host, port)
        self.display = RealTimeDisplay(self.storage)
        
        # Set up receiver callbacks
        self.receiver.set_metrics_processor(self.processor.process_metrics)
        self.receiver.set_trace_processor(self.processor.process_traces)
        # Note: logs processor calls storage callback with 'log' event type
        def log_storage_callback(log_data):
            self.storage.store_event('log', log_data)
        
        self.receiver.set_logs_processor(lambda request: self.processor.process_logs(request))
        
        # Demo data generator
        if self.demo_mode:
            self.sample_generator = SampleDataGenerator()
    
    def start(self):
        """Start the telemetry collector."""
        print_welcome()
        
        if self.demo_mode:
            print("Running in DEMO mode - generating sample data")
            self._start_demo_mode()
        else:
            print_startup_info()
            self._start_receiver()
    
    def _start_receiver(self):
        """Start the OTLP receiver and display loop."""
        try:
            # Start OTLP receiver
            self.receiver.start()
            self.running = True
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Main display loop
            while self.running:
                try:
                    self.display.display_dashboard()
                    time.sleep(2)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logging.error(f"Error in display loop: {e}")
                    time.sleep(1)
        
        except Exception as e:
            logging.error(f"Failed to start receiver: {e}")
            sys.exit(1)
        
        finally:
            self._cleanup()
    
    def _start_demo_mode(self):
        """Start demo mode with sample data generation."""
        try:
            # Generate continuous sample data
            self.sample_generator.generate_continuous_data(
                self.storage.store_event,
                interval_seconds=3,
                num_sessions=2
            )
            
            self.running = True
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            print("Demo data generation started. Press Ctrl+C to stop.")
            print()
            
            # Main display loop
            while self.running:
                try:
                    self.display.display_dashboard()
                    time.sleep(2)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logging.error(f"Error in display loop: {e}")
                    time.sleep(1)
        
        except Exception as e:
            logging.error(f"Error in demo mode: {e}")
            sys.exit(1)
        
        finally:
            self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
    
    def stop(self):
        """Stop the telemetry collector."""
        self.running = False
    
    def _cleanup(self):
        """Clean up resources."""
        print("\nShutting down telemetry collector...")
        
        if not self.demo_mode and self.receiver:
            self.receiver.stop()
        
        # Display final summary
        print("\n" + "="*60)
        print("FINAL SESSION SUMMARY")
        print("="*60)
        self.display.display_summary()
        
        print("Telemetry collector stopped.")
    
    def show_sessions(self):
        """Show all captured sessions."""
        self.display.display_summary()
    
    def show_session(self, session_id: str):
        """Show details for a specific session."""
        self.display.display_session_details(session_id)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Development Analytics - Claude Code Telemetry Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Start collector on default port 4317
  %(prog)s --port 4318              # Start collector on custom port
  %(prog)s --demo                   # Run with sample data (no Claude Code needed)
  %(prog)s --log-level DEBUG        # Enable debug logging
  %(prog)s --log-file collector.log # Log to file
        """
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind OTLP receiver (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=4317,
        help="Port for OTLP receiver (default: 4317)"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with sample data generation"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log to file (default: console only)"
    )
    
    parser.add_argument(
        "--show-sessions",
        action="store_true",
        help="Show all captured sessions and exit"
    )
    
    parser.add_argument(
        "--show-session",
        help="Show details for specific session ID and exit"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Create collector
    collector = TelemetryCollector(
        host=args.host,
        port=args.port,
        demo_mode=args.demo
    )
    
    # Handle one-time commands
    if args.show_sessions:
        collector.show_sessions()
        return
    
    if args.show_session:
        collector.show_session(args.show_session)
        return
    
    # Start main collector
    collector.start()


if __name__ == "__main__":
    main()