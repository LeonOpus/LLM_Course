"""
代码执行器工具 - 安全执行Python代码进行数据分析
"""
import os
import sys
import io
import base64
import traceback
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class CodeExecutorTool:
    """Python代码执行器"""
    
    name = "code_executor"
    description = """执行Python代码进行数据分析和可视化。适用于：
    - 数据计算和统计分析
    - 生成图表和可视化
    - 复杂的数据处理逻辑
    - 财务指标计算"""
    
    def __init__(self, timeout: int = 30, max_output: int = 10000):
        self.timeout = timeout
        self.max_output = max_output

        # 确保输出目录存在（使用相对路径）
        self.output_dir = "output/charts"
        os.makedirs(self.output_dir, exist_ok=True)

        # 预定义的安全导入
        self.safe_imports = {
            'pandas': 'pd',
            'numpy': 'np',
            'matplotlib.pyplot': 'plt',
            'json': 'json',
            'math': 'math',
            'datetime': 'datetime',
            'statistics': 'statistics',
        }
        
        # 禁止的模块
        self.forbidden_modules = {
            'os', 'subprocess', 'shutil', 'sys', 'socket', 
            'requests', 'urllib', 'http', 'ftplib', 'smtplib',
            '__builtins__', 'eval', 'exec', 'compile', 'open'
        }
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局变量环境"""
        import pandas as pd
        import numpy as np
        import json
        import math
        from datetime import datetime, timedelta
        import statistics
        
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sorted': sorted,
                'reversed': reversed,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'format': format,
            },
            'pd': pd,
            'np': np,
            'plt': plt,
            'json': json,
            'math': math,
            'datetime': datetime,
            'timedelta': timedelta,
            'statistics': statistics,
            'OUTPUT_DIR': self.output_dir,  # 图表输出目录
        }
        
        return safe_globals
    
    def _check_code_safety(self, code: str) -> Optional[str]:
        """检查代码安全性"""
        for forbidden in self.forbidden_modules:
            if f"import {forbidden}" in code or f"from {forbidden}" in code:
                return f"禁止导入模块: {forbidden}"
            if f"__{forbidden}__" in code:
                return f"禁止使用: __{forbidden}__"
        
        # 检查危险操作
        dangerous_patterns = [
            ('open(', '禁止使用 open() 函数'),
            ('eval(', '禁止使用 eval() 函数'),
            ('exec(', '禁止使用 exec() 函数'),
            ('compile(', '禁止使用 compile() 函数'),
            ('__import__', '禁止使用 __import__'),
        ]
        
        for pattern, message in dangerous_patterns:
            if pattern in code:
                return message
        
        return None
    
    def _preprocess_code(self, code: str) -> str:
        """预处理代码，移除已导入模块的import语句"""
        import re

        # 已预导入的模块
        preloaded = {
            'pandas': 'pd',
            'numpy': 'np',
            'matplotlib.pyplot': 'plt',
            'matplotlib': None,
            'json': 'json',
            'math': 'math',
            'datetime': None,
            'statistics': 'statistics',
        }

        lines = code.split('\n')
        processed_lines = []

        for line in lines:
            stripped = line.strip()
            skip = False

            # 检查是否是导入语句
            if stripped.startswith('import ') or stripped.startswith('from '):
                for module in preloaded:
                    if f'import {module}' in stripped or f'from {module}' in stripped:
                        skip = True
                        break

            if not skip:
                processed_lines.append(line)

        return '\n'.join(processed_lines)

    def run(self, code: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行Python代码

        Args:
            code: Python代码
            data: 可选的数据输入（将作为变量data注入）

        Returns:
            执行结果字典
        """
        # 安全检查
        safety_error = self._check_code_safety(code)
        if safety_error:
            return {
                "success": False,
                "error": safety_error,
                "output": "",
                "figures": []
            }

        # 预处理代码，移除已导入模块的import语句
        code = self._preprocess_code(code)

        # 创建安全环境
        safe_globals = self._create_safe_globals()
        
        # 注入数据 (始终注入，即使为空)
        safe_globals['data'] = data if data else []
        
        # 捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # 清除之前的图形
        plt.close('all')
        
        result = {
            "success": True,
            "output": "",
            "error": "",
            "figures": [],
            "variables": {}
        }
        
        # 实现code执行的核心逻辑
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals)
            
            # 获取输出
            result["output"] = stdout_capture.getvalue()[:self.max_output]
            result["error"] = stderr_capture.getvalue()
            
            # 获取生成的图形
            figures = [plt.figure(num) for num in plt.get_fignums()]
            for i, fig in enumerate(figures):
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                result["figures"].append({
                    "index": i,
                    "base64": img_base64,
                    "format": "png"
                })
                buf.close()
            
            # 提取结果变量
            result_vars = ['result', 'output', 'answer', 'df', 'summary']
            for var in result_vars:
                if var in safe_globals:
                    val = safe_globals[var]
                    try:
                        # 尝试序列化
                        if hasattr(val, 'to_dict'):
                            result["variables"][var] = val.to_dict()
                        elif hasattr(val, 'tolist'):
                            result["variables"][var] = val.tolist()
                        else:
                            result["variables"][var] = str(val)
                    except:
                        result["variables"][var] = str(val)
            
        except Exception as e:
            result["success"] = False
            result["error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        
        finally:
            plt.close('all')
        
        return result


# 工具函数定义（用于LangGraph）
CODE_EXECUTOR_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "code_executor",
        "description": "执行Python代码进行数据分析和可视化。支持pandas、numpy、matplotlib等库。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的Python代码。可以使用pd(pandas)、np(numpy)、plt(matplotlib.pyplot)等预导入的库。"
                },
                "data": {
                    "type": "object",
                    "description": "可选的输入数据，将作为变量'data'注入到代码中"
                }
            },
            "required": ["code"]
        }
    }
}


if __name__ == "__main__":
    # 测试
    executor = CodeExecutorTool()
    
    # 测试基本计算
    code1 = """
import pandas as pd
import numpy as np

# 创建示例数据
data = {
    'stock': ['工商银行', '招商银行', '贵州茅台'],
    'price': [5.2, 35.8, 1800],
    'pe': [5.0, 7.5, 28.5]
}
df = pd.DataFrame(data)
print("股票数据:")
print(df)
print(f"\\n平均PE: {df['pe'].mean():.2f}")
"""
    
    result = executor.run(code1)
    print("测试1 - 基本计算:")
    print(f"成功: {result['success']}")
    print(f"输出: {result['output']}")
    
    # 测试图表生成
    code2 = """
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

x = ['银行', '白酒', '新能源', '医药', '券商']
y = [15, 8, 25, 18, 12]

plt.figure(figsize=(10, 6))
plt.bar(x, y, color=['blue', 'red', 'green', 'purple', 'orange'])
plt.title('各行业平均PE对比')
plt.xlabel('行业')
plt.ylabel('PE值')
"""
    
    result = executor.run(code2)
    print("\n测试2 - 图表生成:")
    print(f"成功: {result['success']}")
    print(f"生成图表数: {len(result['figures'])}")
    
    # 测试安全检查
    code3 = """
import os
os.system('ls')
"""
    
    result = executor.run(code3)
    print("\n测试3 - 安全检查:")
    print(f"成功: {result['success']}")
    print(f"错误: {result['error']}")
