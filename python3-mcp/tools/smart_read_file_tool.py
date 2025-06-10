# python3_mcp/tools/smart_read_file_tool.py
import os
from python3_mcp.core.tool import BaseTool
from python3_mcp.core import cst_utils # Assuming cst_utils is in core
# from python3_mcp.core.file_timestamps import FileTimestampManager # For type hinting

class SmartReadFilePythonTool(BaseTool):
    DEFAULT_MAX_LINES_RAW = 2000 # For fallback raw reading

    @property
    def name(self) -> str:
        return "smart_read_file_python"

    @property
    def description(self) -> str:
        return (
            "Reads Python files with language awareness. Provides a collapsed view "
            "(class/function signatures) by default. Can expand specific forms based on "
            "name or content patterns. Falls back to raw text reading for non-Python files "
            "or if 'collapsed_view' is false."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path to the file."
                },
                "collapsed_view": {
                    "type": "boolean",
                    "description": "Whether to provide a collapsed (signatures only) view. Default: true.",
                    "default": True
                },
                "name_pattern": {
                    "type": "string",
                    "description": "Regex to match top-level form names (functions, classes) for expansion in collapsed view."
                },
                "content_pattern": {
                    "type": "string",
                    "description": "Regex to match content within top-level forms for expansion in collapsed view."
                },
                # Raw read params from ReadFileTool, for fallback
                "line_offset": { "type": "integer", "default": 0 },
                "limit": { "type": "integer", "default": self.DEFAULT_MAX_LINES_RAW }
            },
            "required": ["path"]
        }

    def _is_python_file(self, file_path: str) -> bool:
        return file_path.endswith((".py", ".pyw")) # Basic check

    def _raw_read_file(self, file_path: str, line_offset: int, limit: int, execution_context: any) -> dict:
        # Conceptual: This would call a shared raw_read_file logic or the ReadFileTool directly
        # For now, simulate a simple version.
        print(f"[SmartReadFilePythonTool] Conceptual: Falling back to raw read for {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i < line_offset: continue
                    if len(lines) >= limit: break
                    lines.append(line.rstrip('\n'))

            # Timestamp interaction
            if execution_context and hasattr(execution_context, 'timestamp_manager'):
                execution_context.timestamp_manager.record_file_read(os.path.abspath(file_path))

            return {'result': ["\n".join(lines)], 'error': False}
        except Exception as e:
            return {'message': f"Raw read error for {file_path}: {str(e)}", 'error': True}


    def execute(self, params: dict, execution_context: any = None) -> dict:
        file_path = params.get("path")
        if not file_path:
            return {'message': "Missing 'path' parameter.", 'error': True}

        abs_file_path = os.path.abspath(file_path)
        if not os.path.exists(abs_file_path) or not os.path.isfile(abs_file_path):
            return {'message': f"File not found or is not a file: {abs_file_path}", 'error': True}

        use_collapsed_view = params.get("collapsed_view", True)
        name_pattern = params.get("name_pattern")
        content_pattern = params.get("content_pattern")

        if self._is_python_file(abs_file_path) and use_collapsed_view:
            try:
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    code_str = f.read() # Read the full code string

                # Pass the code string to parse_python_code_to_cst
                module_cst = cst_utils.parse_python_code_to_cst(code_str)

                # Pass module_cst AND code_str to extract_collapsed_view_with_patterns
                collapsed_content = cst_utils.extract_collapsed_view_with_patterns(
                    module_cst, code_str, name_pattern, content_pattern
                )

                # Timestamp interaction (even for smart read)
                if execution_context and hasattr(execution_context, 'timestamp_manager'):
                    execution_context.timestamp_manager.record_file_read(abs_file_path)

                return {'result': [collapsed_content], 'error': False}
            except Exception as e:
                # Fallback to raw read on CST processing error, or return error
                # For now, let's return a specific error for CST issues
                return {'message': f"Error processing Python file with LibCST {abs_file_path}: {str(e)}", 'error': True}
        else:
            # Fallback to raw reading for non-Python files or non-collapsed view
            line_offset = params.get("line_offset", 0)
            limit = params.get("limit", self.DEFAULT_MAX_LINES_RAW)
            return self._raw_read_file(abs_file_path, line_offset, limit, execution_context)
