import pkgutil
import traceback

from bot import bot

for m in pkgutil.iter_modules(['cogs']):
    module = f"cogs.{m.name}" # sadly no proper way to do this
    try:
        bot.load_extension(module)
        print(f"Loaded extension '{m.name}'")
    except Exception as e:
        exception = traceback.format_exc()
        bot.logger.error(f"Failed to load extension {m.name}\n{exception}")

bot.run()
