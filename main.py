import pkgutil
import traceback

from bot import bot

for m in pkgutil.iter_modules(['cogs']):
    try:
        bot.load_extension(f"{m.module_finder.path}.{m.name}") # type: ignore
        print(f"Loaded extension '{m.name}'")
    except Exception as e:
        exception = traceback.format_exc()
        bot.logger.error(f"Failed to load extension {m.name}\n{exception}")

bot.run()
