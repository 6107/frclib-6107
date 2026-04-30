"""
Log Data Receiver Module

This module defines the abstract base class for log data receivers. Log receivers are
responsible for consuming and processing telemetry data from the logging system. They
act as sinks in the logging pipeline, handling entries at specific timestamps.

Log receivers are used in several contexts:
- Real robot: Receiving and writing logs to NetworkTables or USB storage
- Simulation: Recording simulation data during desktop testing  
- Replay: Processing logged data during log replay analysis

Subclasses implement the specific I/O and processing logic for each backend.
"""

from lib_6107.pykit.logtable import LogTable


class LogDataReceiver:
    """
    Abstract base class defining the interface for log data receivers.
    
    Log receivers consume LogTable entries from the pykit logging system and
    perform backend-specific processing (writing to files, sending over network,
    storing in memory, etc.). All log data flows through registered receivers
    during the logging pipeline.
    
    Subclasses should implement the three lifecycle methods to handle initialization,
    timestamp-keyed log table processing, and cleanup.
    
    Attributes:
        timestamp_key (str): The standard key used to retrieve the timestamp value
            from each LogTable. Default: "/Timestamp". The timestamp represents
            the moment in time (typically seconds since epoch or match start) for
            the log entry being processed.
            
    Example:
        ```python
        class MyLogReceiver(LogDataReceiver):
            def __init__(self):
                self.log_file = None
            
            def start(self):
                # Called once at logging initialization
                self.log_file = open("robot.log", "w")
            
            def put_table(self, table: LogTable):
                # Called once per timestamp with all logged data
                timestamp = table.get(self.timestampKey, 0.0)
                self.log_file.write(f"{timestamp}: {table}\\n")
            
            def end(self):
                # Called once at logging shutdown
                if self.log_file:
                    self.log_file.close()
        ```
    """

    timestamp_key: str = "/Timestamp"
    """
    The standard LogTable key for retrieving timestamp values from log entries.
    
    Each LogTable passed to put_table() should contain the timestamp at this key.
    This allows receivers to associate data with a specific point in time.
    """

    def start(self):
        """
        Called once when the logging process starts (typically in robotInit).
        
        Subclasses should override this method to perform one-time initialization
        tasks such as opening files, establishing connections, allocating buffers,
        or registering with external systems.
        
        This is guaranteed to be called before any put_table() calls.
        """

    def end(self):
        """
        Called once when the logging process ends (typically at robot shutdown).
        
        Subclasses should override this method to perform cleanup tasks such as
        flushing buffers, closing files, disconnecting sockets, or finalizing data.
        
        This is guaranteed to be called after the last put_table() call.
        """

    def put_table(self, table: LogTable):
        """
        Processes a single LogTable entry containing one timestamp's worth of data.
        
        This method is called once per timestamp (typically at 50 Hz during robot
        operation) with a LogTable containing all telemetry data recorded at that
        moment. Subclasses implement backend-specific logic to store, transmit,
        process, or transform this data.
        
        Args:
            table (LogTable): A LogTable snapshot containing all logged values at
                a specific timestamp. The timestamp itself is available at the
                timestampKey ("/Timestamp"). Receivers should iterate over table
                entries and handle them according to their backend requirements.
                
        Note:
            - This method should complete quickly to avoid blocking the robot main loop
            - Subclasses should handle the case where expected keys are missing
            - Multiple receivers may process the same table in sequence
            - The timestamp can be retrieved via: table.get(self.timestampKey, 0.0)
        """