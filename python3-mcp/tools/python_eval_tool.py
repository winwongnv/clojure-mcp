# python3_mcp/tools/python_eval_tool.py
from python3_mcp.core.tool import BaseTool # Assuming BaseTool path
# from python3_mcp.kernel.manager import KernelManager # For type hinting if needed

class PythonEvalTool(BaseTool):
    @property
    def name(self) -> str:
        return "python_eval"

    @property
    def description(self) -> str:
        return "Evaluates a string of Python code in the connected Python kernel and returns the output or error."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code string to evaluate."
                }
            },
            "required": ["code"]
        }

    def execute(self, params: dict, execution_context: any = None) -> dict:
        code_to_execute = params.get("code")
        if not code_to_execute:
            return {'message': "Missing 'code' parameter.", 'error': True}

        if not execution_context or not hasattr(execution_context, 'kernel_manager'):
            return {'message': "KernelManager not found in execution_context.", 'error': True}

        kernel_manager = execution_context.kernel_manager

        try:
            # Assume kernel_manager.execute_code returns a dict with stdout, stderr, result, error_info
            # Example: kernel_response = {'stdout': 'Hello
', 'stderr': '', 'result': None, 'error_info': None}
            # Example error: kernel_response = {'stdout': '', 'stderr': '', 'result': None,
            #                                'error_info': {'ename': 'SyntaxError', 'evalue': 'invalid syntax',
            #                                               'traceback': ['line 1...', 'line 2...']}}
            kernel_response = kernel_manager.execute_code(code_to_execute)

            output_lines = []
            if kernel_response.get('stdout'):
                output_lines.append(f"STDOUT:\n{kernel_response['stdout'].strip()}")
            if kernel_response.get('stderr'):
                output_lines.append(f"STDERR:\n{kernel_response['stderr'].strip()}")

            execution_result = kernel_response.get('result')
            if execution_result is not None: # Could be None for successful execution with no explicit return
                output_lines.append(f"RESULT:\n{execution_result}")

            error_info = kernel_response.get('error_info')
            if error_info:
                tb_str = "\n".join(error_info.get('traceback', []))
                error_message = f"ERROR: {error_info.get('ename', 'UnknownError')}: {error_info.get('evalue', '')}\nTraceback:\n{tb_str}"
                # If there was an error, stdout/stderr might still be relevant, so include them if present
                if output_lines:
                    full_message = f"{error_message}\n\nCaptured Output before error:\n" + "\n".join(output_lines)
                    return {'message': full_message, 'error': True}
                return {'message': error_message, 'error': True}

            if not output_lines: # Handle cases where there's no stdout/stderr/result but also no error
                return {'result': ["<No output>"], 'error': False}

            return {'result': output_lines, 'error': False}

        except Exception as e:
            # Catch unexpected errors in communication or tool logic
            return {'message': f"Error in PythonEvalTool: {str(e)}", 'error': True}

# Potential decorator for registration (conceptual)
# from python3_mcp.core.registry import register_tool
# @register_tool
# class PythonEvalTool(BaseTool): ...
