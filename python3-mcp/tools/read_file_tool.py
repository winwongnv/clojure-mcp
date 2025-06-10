# python3_mcp/tools/read_file_tool.py
import os
from python3_mcp.core.tool import BaseTool
# from python3_mcp.core.file_timestamps import FileTimestampManager # For type hinting

class ReadFileTool(BaseTool):
    DEFAULT_MAX_LINES = 2000
    DEFAULT_MAX_LINE_LENGTH = 1000 # Placeholder, actual truncation not in this basic version

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (f"Reads the content of a specified file. "
                f"Can read a segment of the file using line_offset and limit. "
                f"Tracks file read timestamps for edit safety. "
                f"Defaults to reading up to {self.DEFAULT_MAX_LINES} lines.")

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file."
                },
                "line_offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-indexed). Default: 0.",
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": f"Maximum number of lines to read. Default: {self.DEFAULT_MAX_LINES}.",
                    "default": self.DEFAULT_MAX_LINES
                }
            },
            "required": ["path"]
        }

    def execute(self, params: dict, execution_context: any = None) -> dict:
        file_path = params.get("path")
        line_offset = params.get("line_offset", 0)
        limit = params.get("limit", self.DEFAULT_MAX_LINES)

        if not file_path:
            return {'message': "Missing 'path' parameter.", 'error': True}

        try:
            abs_file_path = os.path.abspath(file_path) # Normalize path
            if not os.path.exists(abs_file_path):
                return {'message': f"File not found: {abs_file_path}", 'error': True}
            if not os.path.isfile(abs_file_path):
                return {'message': f"Path is not a file: {abs_file_path}", 'error': True}

            lines = []
            with open(abs_file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < line_offset:
                        continue
                    if len(lines) >= limit:
                        break
                    lines.append(line.rstrip('\n')) # Store without trailing newline for consistency

            content = "\n".join(lines)

            # Interact with FileTimestampManager
            if execution_context and hasattr(execution_context, 'timestamp_manager'):
                timestamp_manager = execution_context.timestamp_manager
                timestamp_manager.record_file_read(abs_file_path)
            else:
                # This case should ideally be handled by server setup ensuring manager is present
                print(f"[ReadFileTool] Warning: FileTimestampManager not found in execution_context for {abs_file_path}")


            return {'result': [content], 'error': False}

        except Exception as e:
            return {'message': f"Error reading file {file_path}: {str(e)}", 'error': True}
