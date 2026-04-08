#!/usr/bin/env python3
"""
WASEEM CODE GENERATOR - Type-Safe Code Synthesis
Template-based generation, refactoring, documentation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GeneratedCode:
    """Generated code result"""
    code: str
    language: str
    description: str
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    tests: Optional[str] = None
    documentation: Optional[str] = None
    confidence: float = 0.85


@dataclass
class Template:
    """Code template"""
    name: str
    pattern: str
    placeholders: List[str]
    description: str


class CodeTemplates:
    """Built-in code templates"""
    
    PYTHON_CLASS = '''"""
{description}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class {class_name}:
    """{class_doc}"""
    {fields}
    
    def {method_name}(self{method_params}) -> {return_type}:
        """{method_doc}"""
        {method_body}
'''

    PYTHON_FUNCTION = '''def {function_name}({params}) -> {return_type}:
    """
    {description}
    
    Args:
        {args_doc}
    
    Returns:
        {return_doc}
    """
    {body}
'''

    PYTHON_TEST = '''"""
Tests for {module_name}
"""

import pytest
from {module_import} import {class_or_function}


class Test{test_class_name}:
    """Test suite for {class_or_function}"""
    
    def test_{test_name}_success(self):
        """Test successful execution"""
        # Arrange
        {arrange}
        
        # Act
        result = {act}
        
        # Assert
        {assertions}
    
    def test_{test_name}_edge_case(self):
        """Test edge case handling"""
        # TODO: Add edge case test
        pass
'''

    TYPESCRIPT_INTERFACE = '''/**
 * {description}
 */
export interface {interface_name} {{
    {fields}
}}
'''

    TYPESCRIPT_CLASS = '''/**
 * {description}
 */

export class {class_name} {{
    {fields}
    
    constructor({constructor_params}) {{
        {constructor_body}
    }}
    
    {methods}
}}
'''

    REFACTOR_EXTRACT_METHOD = '''
# Extracted method: {method_name}
def {method_name}({params}) -> {return_type}:
    """{description}"""
    {body}
'''

    ERROR_HANDLER = '''def handle_{error_name}(error: {error_type}) -> {return_type}:
    """
    Handle {error_type} with proper logging and recovery.
    
    Args:
        error: The exception instance
        
    Returns:
        {return_doc}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.error("{error_name}: %s", str(error), exc_info=True)
    
    {recovery_logic}
    
    return {default_return}
'''


class CodeGenerator:
    """
    Code generation engine with templates and synthesis
    """
    
    def __init__(self):
        self.templates = CodeTemplates()
        self.generation_history: List[GeneratedCode] = []
    
    def generate_class(
        self,
        class_name: str,
        description: str,
        fields: List[Dict[str, str]],
        methods: List[Dict[str, Any]],
        language: str = "python"
    ) -> GeneratedCode:
        """Generate a class definition"""
        
        if language == "python":
            return self._generate_python_class(class_name, description, fields, methods)
        elif language in ("typescript", "ts"):
            return self._generate_typescript_class(class_name, description, fields, methods)
        else:
            return GeneratedCode(
                code="",
                language=language,
                description=f"Unsupported language: {language}",
                confidence=0.0
            )
    
    def _generate_python_class(
        self,
        class_name: str,
        description: str,
        fields: List[Dict[str, str]],
        methods: List[Dict[str, Any]]
    ) -> GeneratedCode:
        """Generate Python class"""
        
        # Format fields
        field_lines = []
        for f in fields:
            field_type = f.get("type", "Any")
            default = f.get("default", None)
            if default is not None:
                field_lines.append(f"{f['name']}: {field_type} = {default}")
            else:
                field_lines.append(f"{f['name']}: {field_type}")
        
        fields_str = "\n    ".join(field_lines) if field_lines else "pass"
        
        # Format methods
        method_codes = []
        method_names = []
        for m in methods:
            method_code = self._generate_method(m)
            method_codes.append(method_code)
            method_names.append(m.get("name", "unknown"))
        
        # Build class
        code = f'''"""
{description}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class {class_name}:
    """{description}"""
    {fields_str}
    
{''.join(method_codes)}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language="python",
            description=description,
            classes=[class_name],
            functions=method_names,
            confidence=0.9
        )
        
        self.generation_history.append(result)
        return result
    
    def _generate_typescript_class(
        self,
        class_name: str,
        description: str,
        fields: List[Dict[str, str]],
        methods: List[Dict[str, Any]]
    ) -> GeneratedCode:
        """Generate TypeScript class"""
        
        # Format fields
        field_lines = []
        constructor_params = []
        for f in fields:
            ts_type = self._python_to_ts_type(f.get("type", "any"))
            field_lines.append(f"private {f['name']}: {ts_type};")
            constructor_params.append(f"{f['name']}: {ts_type}")
        
        # Format methods
        method_codes = []
        method_names = []
        for m in methods:
            method_code = self._generate_ts_method(m)
            method_codes.append(method_code)
            method_names.append(m.get("name", "unknown"))
        
        code = f'''/**
 * {description}
 */

export class {class_name} {{
    {''.join(field_lines)}
    
    constructor({', '.join(constructor_params)}) {{
        {'; '.join([f"this.{f['name']} = {f['name']}" for f in fields])};
    }}
    
{''.join(method_codes)}
}}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language="typescript",
            description=description,
            classes=[class_name],
            functions=method_names,
            confidence=0.85
        )
        
        self.generation_history.append(result)
        return result
    
    def _generate_method(self, method: Dict[str, Any]) -> str:
        """Generate Python method"""
        name = method.get("name", "method")
        params = method.get("params", [])
        return_type = method.get("return_type", "None")
        doc = method.get("doc", "")
        body = method.get("body", "pass")
        
        param_str = ", ".join(params) if params else ""
        
        return f'''
    def {name}(self{", " if params else ""}{param_str}) -> {return_type}:
        """{doc}"""
        {body}
'''
    
    def _generate_ts_method(self, method: Dict[str, Any]) -> str:
        """Generate TypeScript method"""
        name = method.get("name", "method")
        params = method.get("params", [])
        return_type = self._python_to_ts_type(method.get("return_type", "void"))
        doc = method.get("doc", "")
        body = method.get("body", "// TODO")
        
        param_str = ", ".join(params) if params else ""
        
        return f'''
    /**
     * {doc}
     */
    {name}({param_str}): {return_type} {{
        {body}
    }}
'''
    
    def _python_to_ts_type(self, py_type: str) -> str:
        """Convert Python type to TypeScript type"""
        mapping = {
            "str": "string",
            "int": "number",
            "float": "number",
            "bool": "boolean",
            "list": "Array<any>",
            "dict": "Record<string, any>",
            "None": "void",
            "Any": "any",
            "Optional": "any | null",
        }
        return mapping.get(py_type.lower(), py_type)
    
    def generate_function(
        self,
        name: str,
        description: str,
        params: List[Dict[str, str]],
        return_type: str,
        body: str = "pass",
        language: str = "python"
    ) -> GeneratedCode:
        """Generate a function definition"""
        
        # Format parameters
        param_list = []
        args_doc = []
        for p in params:
            param_list.append(f"{p['name']}: {p.get('type', 'Any')}")
            args_doc.append(f"{p['name']}: {p.get('doc', 'No description')}")
        
        params_str = ", ".join(param_list)
        args_doc_str = "\n        ".join(args_doc)
        
        code = f'''def {name}({params_str}) -> {return_type}:
    """
    {description}
    
    Args:
        {args_doc_str}
    
    Returns:
        {return_type}: Description of return value
    """
    {body}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language=language,
            description=description,
            functions=[name],
            confidence=0.9
        )
        
        self.generation_history.append(result)
        return result
    
    def generate_test(
        self,
        module_name: str,
        class_or_function: str,
        test_cases: List[Dict[str, str]]
    ) -> GeneratedCode:
        """Generate unit tests"""
        
        test_methods = []
        for i, tc in enumerate(test_cases):
            test_name = tc.get("name", f"case_{i}")
            arrange = tc.get("arrange", "# Setup")
            act = tc.get("act", "result = None")
            assertions = tc.get("assert", "assert result is not None")
            
            test_methods.append(f'''
    def test_{test_name}(self):
        """Test {test_name}"""
        # Arrange
        {arrange}
        
        # Act
        {act}
        
        # Assert
        {assertions}
''')
        
        code = f'''"""
Tests for {module_name}
"""

import pytest
from {module_name} import {class_or_function}


class Test{class_or_function}:
    """Test suite for {class_or_function}"""
    
{''.join(test_methods)}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language="python",
            description=f"Tests for {class_or_function}",
            functions=[f"test_{tc.get('name', f'case_{i}')}" for i, tc in enumerate(test_cases)],
            confidence=0.85
        )
        
        self.generation_history.append(result)
        return result
    
    def generate_error_handler(
        self,
        error_type: str,
        description: str,
        recovery_logic: str = "pass",
        default_return: str = "None"
    ) -> GeneratedCode:
        """Generate error handler function"""
        
        error_name = error_type.lower().replace("error", "").strip()
        function_name = f"handle_{error_name}"
        
        code = f'''def {function_name}(error: {error_type}) -> Any:
    """
    Handle {error_type} with proper logging and recovery.
    
    Args:
        error: The exception instance
        
    Returns:
        Fallback value or None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.error("{error_name}: %s", str(error), exc_info=True)
    
    {recovery_logic}
    
    return {default_return}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language="python",
            description=description,
            functions=[function_name],
            confidence=0.85
        )
        
        self.generation_history.append(result)
        return result
    
    def generate_interface(
        self,
        name: str,
        description: str,
        fields: List[Dict[str, str]]
    ) -> GeneratedCode:
        """Generate TypeScript interface"""
        
        field_lines = []
        for f in fields:
            ts_type = self._python_to_ts_type(f.get("type", "any"))
            optional = "?" if f.get("optional", False) else ""
            field_lines.append(f"{f['name']}{optional}: {ts_type};")
        
        code = f'''/**
 * {description}
 */
export interface {name} {{
    {''.join(field_lines)}
}}
'''
        
        result = GeneratedCode(
            code=code.strip(),
            language="typescript",
            description=description,
            confidence=0.9
        )
        
        self.generation_history.append(result)
        return result
    
    def refactor_extract_method(
        self,
        original_code: str,
        method_name: str,
        start_line: int,
        end_line: int,
        description: str = ""
    ) -> GeneratedCode:
        """Extract code into a new method"""
        
        lines = original_code.split('\n')
        extracted = '\n'.join(lines[start_line:end_line])
        
        # Generate new method
        new_method = f'''def {method_name}(self) -> None:
    """{description or 'Extracted method'}"""
    {extracted}
'''
        
        # Replace in original
        modified_code = original_code.replace(extracted, f"self.{method_name}()")
        
        result = GeneratedCode(
            code=new_method,
            language="python",
            description=f"Extracted method: {method_name}",
            functions=[method_name],
            confidence=0.8
        )
        
        self.generation_history.append(result)
        return result
    
    def generate_documentation(
        self,
        code: str,
        style: str = "google"
    ) -> str:
        """Generate documentation for code"""
        
        # Extract structure
        functions = re.findall(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        classes = re.findall(r'class\s+(\w+)', code)
        
        doc_lines = []
        doc_lines.append('"""')
        doc_lines.append('Module Documentation')
        doc_lines.append('')
        
        if classes:
            doc_lines.append('Classes:')
            for cls in classes:
                doc_lines.append(f'    {cls}: Description needed')
            doc_lines.append('')
        
        if functions:
            doc_lines.append('Functions:')
            for func_name, params in functions:
                doc_lines.append(f'    {func_name}({params}): Description needed')
        
        doc_lines.append('"""')
        
        return '\n'.join(doc_lines)
    
    def get_generation_history(self) -> List[Dict[str, Any]]:
        """Get history of generated code"""
        return [
            {
                "language": g.language,
                "description": g.description,
                "functions": g.functions,
                "classes": g.classes,
                "confidence": g.confidence,
                "code_length": len(g.code)
            }
            for g in self.generation_history
        ]


def generate_class(
    class_name: str,
    description: str,
    fields: List[Dict[str, str]],
    methods: List[Dict[str, Any]] = None,
    language: str = "python"
) -> GeneratedCode:
    """Convenience function to generate a class"""
    generator = CodeGenerator()
    return generator.generate_class(
        class_name,
        description,
        fields,
        methods or [],
        language
    )


def generate_function(
    name: str,
    description: str,
    params: List[Dict[str, str]],
    return_type: str,
    body: str = "pass"
) -> GeneratedCode:
    """Convenience function to generate a function"""
    generator = CodeGenerator()
    return generator.generate_function(
        name, description, params, return_type, body
    )


if __name__ == "__main__":
    # Demo
    print("=" * 80)
    print("WASEEM CODE GENERATOR - TYPE-SAFE CODE SYNTHESIS")
    print("=" * 80)
    
    generator = CodeGenerator()
    
    # Generate a class
    print("\n[CLASS GENERATION]")
    result = generator.generate_class(
        class_name="DataProcessor",
        description="Processes and transforms data",
        fields=[
            {"name": "data", "type": "List[Dict[str, Any]]", "default": "field(default_factory=list)"},
            {"name": "config", "type": "Dict[str, Any]", "default": "field(default_factory=dict)"}
        ],
        methods=[
            {
                "name": "process",
                "params": ["item: Dict[str, Any]"],
                "return_type": "Dict[str, Any]",
                "doc": "Process a single data item",
                "body": "return {**item, 'processed': True}"
            },
            {
                "name": "batch_process",
                "params": [],
                "return_type": "List[Dict[str, Any]]",
                "doc": "Process all items",
                "body": "return [self.process(item) for item in self.data]"
            }
        ]
    )
    print(result.code)
    
    # Generate tests
    print("\n[TEST GENERATION]")
    test_result = generator.generate_test(
        module_name="data_processor",
        class_or_function="DataProcessor",
        test_cases=[
            {
                "name": "process_item",
                "arrange": "processor = DataProcessor(data=[{'id': 1}])",
                "act": "result = processor.process({'id': 1})",
                "assert": "assert result['processed'] == True"
            }
        ]
    )
    print(test_result.code)
    
    print("\n[DONE]")
