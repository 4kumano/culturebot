import io
import textwrap
import traceback
import re
from contextlib import redirect_stdout

from discord.ext import commands
from discord.ext.commands import Context


class Debug(commands.Cog, command_attrs=dict(hidden=True, checks=[commands.is_owner()])):
    """A Cog for command debugging. Owner only."""
    def __init__(self, bot):
        self.bot = bot
        self.last_return = None

    async def run_code(self, code: str, env: dict) -> str:
        """Runs provided code returning the str representation of the output.
        
        If the code has a return or is a single line the return is also returned.
        """
        # put it in an async function
        wrapped_code = "async def func():\n" + textwrap.indent(code, '  ')

        try:
            exec(wrapped_code, env)
        except Exception as e:
            return repr(e)

        stream = io.StringIO()
        func = env['func']
        try:
            with redirect_stdout(stream):
                ret = await func()
        except Exception as e:
            return stream.getvalue() + traceback.format_exc()
        
        stdout = stream.getvalue()
        
        if stdout:
            if ret:
                self.last_return = ret
                stdout += '\n' + repr(ret)
            return stdout
        
        try:
            ret = eval(code, env)
            if ret:
                self.last_return = ret
                return repr(ret)
        except:
            pass
        
        return 'None'
    
    _code_re = re.compile(r'(?:```\w{0,2}|`)([^`]+?)(?:```|`)', re.M)
    @commands.command('run')
    async def run(self, ctx: Context, *, string: str = ''):
        """Runs python code in all codeblocks in the message."""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self.last_return,
            
            'pprint': __import__('pprint').pprint,
            'json': __import__('json')
        }
        
        for code in re.findall(self._code_re, string):
            output = await self.run_code(code.strip(), env)
            chunk_size = 1992
            for i in range(0, len(output), chunk_size):
                await ctx.send(f'```\n{output[i:i+chunk_size]}\n```')


def setup(bot):
    bot.add_cog(Debug(bot))
