import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from keep_alive import keep_alive

# Start serwera keep-alive
keep_alive()

# Załaduj zmienne środowiskowe
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Ustawienie intencji
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class SupremeCourtBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
    
    # Override zamiast dekoratora
    async def setup_hook(self):
        # 1) Ładowanie wszystkich cogs
        for fname in os.listdir("./cogs"):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            ext = f"cogs.{fname[:-3]}"
            try:
                await self.load_extension(ext)
                print(f"✅ Załadowano coga: {ext}")
            except Exception as e:
                print(f"❌ Błąd ładowania {ext}: {e}")
        
        # 2) Synchronizacja slash-komend
        try:
            print("🔄 Synchronizacja komend slash...")
            synced = await self.tree.sync()
            print(f"🔁 Zsynchronizowano {len(synced)} komend")
        except Exception as e:
            print(f"❌ Błąd sync: {e}")
    
    async def on_ready(self):
        print(f"🚀 Zalogowano jako {self.user} (ID: {self.user.id})")
        print(f"Bot działa na {len(self.guilds)} serwerach")
        # Pokaż listę dostępnych slash-komend
        print("📋 Dostępne komendy slash:")
        for cmd in self.tree.get_commands():
            print(f" - /{cmd.name}: {cmd.description}")

if __name__ == "__main__":
    bot = SupremeCourtBot()
    
    # Dodaj proste ping, by upewnić się, że bot działa
    @bot.command()
    async def ping(ctx):
        await ctx.send(f"Pong! Opóźnienie: {round(bot.latency * 1000)}ms")
    
    bot.run(TOKEN)