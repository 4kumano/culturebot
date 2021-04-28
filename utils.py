import asyncio
from contextlib import redirect_stdout
import io
from pprint import pprint

def run_code(code: str, globals: dict = None, evaluate: bool=False) -> str:
    """Runs code using exec, returns stdout"""
    loop = asyncio.get_running_loop()
    globals.update({
        'loop': loop,
        'pprint': pprint,
        'asyncio': asyncio
    })
    
    if evaluate:
        try:
            return repr(eval(code,globals))
        except Exception as e:
            return repr(e)
    else:
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                exec(code, globals)
        except Exception as e:
            return repr(e)
        return stream.getvalue() or 'null'
