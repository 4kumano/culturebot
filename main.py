from __future__ import annotations
import pkgutil
import traceback

from bot import bot

for m in pkgutil.iter_modules(['cogs']):
    try:
        module = f"{m.module_finder.path.split('/')[-1]}.{m.name}" # type: ignore
        bot.load_extension(module)
        print(f"Loaded extension '{m.name}'")
    except Exception as e:
        exception = traceback.format_exc()
        bot.logger.error(f"Failed to load extension {m.name}\n{exception}")

bot.run()
