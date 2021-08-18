import argparse
import pkgutil
import traceback

from bot import bot

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--no-webapp', action='store_false', dest='webapp')
parser.add_argument('--extensions', nargs='+')
args = parser.parse_args()

for m in pkgutil.iter_modules(['cogs']):
    if args.extensions and m.name not in args.extensions:
        break
    
    module = f"cogs.{m.name}" # sadly no proper way to do this
    try:
        bot.load_extension(module)
        print(f"Loaded extension '{m.name}'")
    except Exception as e:
        exception = traceback.format_exc()
        bot.logger.error(f"Failed to load extension {m.name}\n{exception}")

bot.run(debug=args.debug, webapp=args.webapp)
