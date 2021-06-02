import inspect
import io
import textwrap
import traceback
import re
from contextlib import redirect_stdout

from utils import chunkify, wrap

import discord
from discord.ext import commands
from discord.ext.commands import Context, Bot


class Debug(commands.Cog, name='debug'):
    """A Cog for command debugging. Owner only."""
    def __init__(self, bot: Bot):
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
    @commands.command('run', hidden=True)
    @commands.is_owner()
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
            
            **globals()
        }
        
        for code in re.findall(self._code_re, string):
            output = await self.run_code(code.strip(), env)
            for chunk in chunkify(output, newlines=True, wrapped=True):
                await ctx.send(chunk)
    
    @commands.command(hidden=True)
    async def getsource(self, ctx: Context, command: str):
        cmd = self.bot.all_commands.get(command)
        if cmd is None:
            await ctx.send(f"Could not find `{command}`")
            return

        for chunk in chunkify(textwrap.dedent(inspect.getsource(cmd.callback))):
            await ctx.send(wrap(chunk, lang='py'))
    
def setup(bot):
    bot.add_cog(Debug(bot))
