# culturebot
culturebot is a bot primarily meant for my private discord server.
This repository is meant rather for showing how the bot works under the hood, if you want to use it yourself you can [invite it](https://discord.com/oauth2/authorize?client_id=803268588387434536&scope=bot&permissions=2046684374)

This bot is simply a way to practice my python and [discord.py](https://discordpy.readthedocs.io/) skills so it has a lot of various features related to my hobbies.

Since I am lazy this bot doesn't have any databases, I try to make it a positive feature but so far it's only been fucking me over.

# how does it work
The custom bot is located in `bot.py`, it dynamically imports all cogs in `cogs`. These cogs all use minor utility functions in `utils`

# running your own instance
If you want to run your own instance of this bot you need to:
- clone the repository with `git clone https://github.com/thesadru/culturebot`
- install dependencies with `pip install -r requirements.txt`
- fill out all secrets required in `config.cfg`, you can see a list of all fields in `config_.cfg`
- run the bot with `python main.py`

