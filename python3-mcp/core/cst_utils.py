# python3_mcp/core/cst_utils.py
# Utilities for working with LibCST Concrete Syntax Trees.

import libcst as cst
import re

class TopLevelCollector(cst.CSTVisitor):
    def __init__(self):
        self.top_level_nodes = []
        # Store (node, start_line, end_line)
        # More precise start/end line calculation might be needed
        self._stack = [] # To keep track of parent nodes

    @property
    def parent_node(self):
        return self._stack[-2] if len(self._stack) >= 2 else None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        # Only top-level functions (could be refined if needed)
        if isinstance(self.parent_node, cst.Module):
             self.top_level_nodes.append({
                "type": "function",
                "name": node.name.value,
                "node": node,
                "start_line": node.start_pos.line,
                "end_line": node.end_pos.line
            })

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        # Only top-level classes
        if isinstance(self.parent_node, cst.Module):
            self.top_level_nodes.append({
                "type": "class",
                "name": node.name.value,
                "node": node,
                "start_line": node.start_pos.line,
                "end_line": node.end_pos.line
            })

    # To handle parent tracking for top-level check
    def visit_node(self, node: cst.CSTNode) -> None:
        self._stack.append(node)
        super().visit_node(node)

    def leave_node(self, original_node: cst.CSTNode) -> None:
        self._stack.pop()
        super().leave_node(original_node)


def _get_params_str(params_node: cst.Parameters) -> str:
    # Simplified: just join param names
    # A real version would handle types, defaults, *args, **kwargs
    param_names = []
    for p in params_node.params:
        # p is cst.Param
        if isinstance(p.name, cst.Name):
            param_names.append(p.name.value)
        # elif isinstance(p.name, cst.Param): # This condition is incorrect for *args, **kwargs
        #     param_names.append(p.name.name.value if isinstance(p.name.name, cst.Name) else str(p.name.name))

    if params_node.star_arg: # e.g. *args
        if isinstance(params_node.star_arg, cst.Name):
            param_names.append(f"*{params_node.star_arg.value}")
        elif isinstance(params_node.star_arg, cst.Param): # Actually *args or *
             param_names.append(f"*{params_node.star_arg.name.value}")


    if params_node.star_kwarg: # e.g. **kwargs
         if isinstance(params_node.star_kwarg.name, cst.Name):
            param_names.append(f"**{params_node.star_kwarg.name.value}")


    return ", ".join(param_names)

def _get_decorators_str_list(decorator_nodes) -> list[str]:
    decs = []
    for dec_node in decorator_nodes: # dec_node is cst.Decorator
        # Simplified: Attempt to reconstruct decorator string
        # This can get very complex for nested calls or attributes
        try:
            decs.append(f"@{dec_node.decorator.get_code().strip()}")
        except Exception:
            decs.append("@...") # Fallback for complex decorators
    return decs

def _get_bases_str_list(base_nodes) -> list[str]:
    bases = []
    for base_node in base_nodes: # base_node is cst.Arg
        try:
            bases.append(base_node.value.get_code().strip())
        except Exception:
            bases.append("...") # Fallback
    return bases


def parse_python_code_to_cst(code: str) -> cst.Module:
    try:
        return cst.parse_module(code)
    except cst.ParserSyntaxError as e:
        # Or raise a custom exception
        raise ValueError(f"LibCST parsing failed: {e}")


def extract_collapsed_view_with_patterns(
    module_cst: cst.Module,
    code_str: str, # Original code string for full form extraction
    name_pattern: str = None,
    content_pattern: str = None # Placeholder for future use
) -> str:
    collector = TopLevelCollector()
    # Need to ensure the parent stack logic is correctly managed by the visit method
    # For top-level, parent_node in collector methods will be the module_cst itself.
    # The provided TopLevelCollector needs its _stack to be initialized with the root.
    # However, LibCST's visit method handles this internally.
    # We modify TopLevelCollector to correctly use the parent provided by the visitor pattern.

    # A simpler way to ensure parent tracking within the visitor if needed,
    # or rely on the fact that visit_FunctionDef is only called for functions.
    # For top-level functions/classes, their parent *is* the Module.
    # So the check 'isinstance(self.parent_node, cst.Module)' in the visitor is key.

    wrapper = cst.metadata.MetadataWrapper(module_cst)
    wrapper.visit(collector) # collector.top_level_nodes will be populated

    output_parts = []
    name_re = None
    if name_pattern:
        try:
            name_re = re.compile(name_pattern)
        except re.error:
            pass

    code_lines = code_str.splitlines(True)

    for item in collector.top_level_nodes:
        node = item["node"]
        form_name = item["name"]
        form_type = item["type"]

        name_match = name_re and name_re.search(form_name)
        # content_match: for now, only name_match determines expansion
        expand_form = bool(name_match)

        decorators_str_list = _get_decorators_str_list(node.decorators) if hasattr(node, 'decorators') and node.decorators else []

        for dec_str in decorators_str_list:
            output_parts.append(dec_str)

        if form_type == "function":
            func_node: cst.FunctionDef = node
            async_prefix = "async " if func_node.asynchronous else ""
            params_str = _get_params_str(func_node.params)
            returns_str = ""
            if func_node.returns:
                try:
                    # Use code_for_node on the original module if available, or get_code on node itself
                    returns_str = f" -> {module_cst.code_for_node(func_node.returns.annotation)}"
                except Exception:
                    returns_str = f" -> ..."

            if expand_form:
                start_idx = item["start_line"] - 1
                end_idx = item["end_line"]
                # Ensure all decorators are part of the slice if not handled above
                # This might require adjusting start_idx if decorators are not part of node's line info
                first_dec_line = item["start_line"]
                if decorators_str_list and hasattr(node.decorators[0], 'start_pos'):
                    first_dec_line = node.decorators[0].start_pos.line

                start_idx = min(start_idx, first_dec_line -1)
                output_parts.append("".join(code_lines[start_idx:end_idx]))
            else:
                output_parts.append(f"{async_prefix}def {form_name}({params_str}){returns_str}: ...")

        elif form_type == "class":
            class_node: cst.ClassDef = node
            bases = _get_bases_str_list(class_node.bases) if class_node.bases else []
            bases_str = f"({', '.join(bases)})" if bases else ""

            if expand_form:
                start_idx = item["start_line"] - 1
                end_idx = item["end_line"]
                first_dec_line = item["start_line"]
                if decorators_str_list and hasattr(node.decorators[0], 'start_pos'):
                    first_dec_line = node.decorators[0].start_pos.line

                start_idx = min(start_idx, first_dec_line-1)
                output_parts.append("".join(code_lines[start_idx:end_idx]))
            else:
                output_parts.append(f"class {form_name}{bases_str}: ...")

        output_parts.append("\n")

    return "\n".join(output_parts).strip()
