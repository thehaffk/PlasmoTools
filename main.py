import disnake
from disnake.ext import commands
import settings
import os

intents = disnake.Intents.all()

bot = commands.Bot(owner_ids=[737501414141591594, 222718720127139840, 191836876980748298],
                   activity=disnake.Activity(type=disnake.ActivityType.watching, text='kto'),
                   intents=intents,
                   sync_commands=True,
                   sync_permissions=True,
                   )

for file in os.listdir('./cogs'):
    if file.endswith(".py"):
        try:
            bot.load_extension(f"cogs.{file[:-3]}")
            print(f"Загружен: {file}")
        except Exception as e:
            print(f"Не удалось загрузить: {file} по причине {e}")

bot.run(settings.token)
