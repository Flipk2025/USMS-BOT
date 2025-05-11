import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta
import traceback
import hashlib
import asyncio

class ocena(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Słownik przechowujący informacje o ostatnio wysłanych wiadomościach
        # Klucz: hash treści, Wartość: (timestamp, channel_id)
        self.recent_messages = {}
        # Interwał czasu (w sekundach) w ramach którego uznajemy wiadomości za duplikaty
        self.duplicate_window = 5

    def _generate_content_hash(self, data, godzina, opis, plusy, minusy, ocena):
        """Generuje unikalny hash na podstawie parametrów rozprawy"""
        content = f"{data}-{godzina}-{opis}-{plusy}-{minusy}-{ocena}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_duplicate(self, content_hash, channel_id):
        """Sprawdza, czy ta sama wiadomość została niedawno wysłana na dany kanał"""
        now = datetime.now()
        if content_hash in self.recent_messages:
            timestamp, msg_channel_id = self.recent_messages[content_hash]
            if msg_channel_id == channel_id:
                # Sprawdź czy wiadomość została wysłana w ciągu ostatnich X sekund
                if (now - timestamp) < timedelta(seconds=self.duplicate_window):
                    return True
        
        # Zapisz informację o aktualnej wiadomości
        self.recent_messages[content_hash] = (now, channel_id)
        
        # Usuwanie starych wpisów (starszych niż minuta)
        to_remove = []
        for hash_key, (msg_time, _) in self.recent_messages.items():
            if (now - msg_time) > timedelta(minutes=1):
                to_remove.append(hash_key)
        
        for key in to_remove:
            del self.recent_messages[key]
            
        return False

    @app_commands.command(name="ocena", description="Wysyła ocene pracy USSS")
    @app_commands.describe(
        data="Data w formacie DD/MM/RRRR",
        godzina="Godzina w formacie HH:MM (24h)",
        opis="Opisz swoje doświadczenie i rekomendacje itp.",
        plusy="Plusy",
        minusy="Minusy",
        ocena="Końcowa Ocena w skali 0-10"
    )
    async def ocena(
        self, interaction: discord.Interaction,
        data: str, godzina: str,
        opis: str, plusy: str,
        minusy: str, ocena: str
    ):
        print(f"🔔 /ocena callback - ID interakcji: {interaction.id}")

        # Opóźnienie, aby uniknąć problemów z wyścigiem
        await asyncio.sleep(0.1)

        try:
            # Sprawdź uprawnienia
            allowed_role_id = 1371066624651558916
            if allowed_role_id not in [r.id for r in interaction.user.roles]:
                await interaction.response.send_message(
                    "Nie masz uprawnień.", ephemeral=True
                )
                return

            # Spróbuj sparsować datę i godzinę
            try:
                # Parsujemy datę jako lokalną (UTC+2), a następnie odejmujemy offset
                # by uzyskać prawidłowy czas UTC
                dt_obj = datetime.strptime(f"{data} {godzina}", "%d/%m/%Y %H:%M")

                # Tworzony jest czas lokalny, trzeba odjąć 2 godziny, by uzyskać poprawny UTC
                # dla Discord timestamp
                poland_offset = timedelta(hours=2)  # UTC+2 dla czasu polskiego
                utc_time = dt_obj - poland_offset

                # Konwersja na timestamp
                timestamp = int(utc_time.replace(tzinfo=timezone.utc).timestamp())
            except ValueError:
                await interaction.response.send_message(
                    "Błędny format daty/godziny.", ephemeral=True
                )
                return

            # Sprawdź czy kanał sądu istnieje
            court_channel_id = 1371145098674573332
            court_channel = self.bot.get_channel(court_channel_id)
            if not court_channel:
                await interaction.response.send_message(
                    "Brak kanału.", ephemeral=True
                )
                return

            # Generuj hash dla tej wiadomości
            content_hash = self._generate_content_hash(
                data, godzina, opis, plusy, minusy, ocena
            )

            # Sprawdź czy to nie duplikat
            if self._is_duplicate(content_hash, court_channel_id):
                print(f"⚠️ Wykryto duplikat wiadomości [hash: {content_hash}] - ignoruję")
                await interaction.response.send_message(
                    f"ocena już została ogłoszona na {court_channel.mention}.",
                    ephemeral=True
                )
                return

            # Przygotuj treść wiadomości
            content = (
                "``` ```\n"
                "# OCENA PRACY USSS\n\n"
                f"**Data:** {data} (<t:{timestamp}:R>)\n"
                f"**Godzina:** {godzina}\n"
                f"### Opis doświadczeń, rekomendacje:\n ```{opis}```\n"
                f"### Plusy:\n ```{plusy}```\n"
                f"### Minusy:\n ```{minusy}```\n"
                f"## Ogólna ocena w skali 0-10: *{ocena}*\n"
                "``` ```\n"
                "||<@&1371145584416915467>||"
            )

            # Wyślij wiadomość na kanał sądu
            await court_channel.send(content)

            # Odpowiedź dla użytkownika
            try:
                await interaction.response.send_message(
                    f"Ocena została wysłana.",
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                # Jeśli interakcja już została obsłużona, spróbuj użyć followup
                await interaction.followup.send(
                    f"Ocena została wysłana.",
                    ephemeral=True
                )

        except Exception as e:
            # Pełne logowanie błędu
            error_msg = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(f"❌ Błąd podczas przetwarzania komendy /ocena:\n{error_msg}")

            try:
                # Próba poinformowania użytkownika o błędzie
                try:
                    await interaction.response.send_message(
                        "Wystąpił błąd podczas przetwarzania komendy. Zgłoś to administracji.",
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        "Wystąpił błąd podczas przetwarzania komendy. Zgłoś to administracji.",
                        ephemeral=True
                    )
            except:
                # Jeśli nawet to się nie powiedzie, po prostu zaloguj
                print("❌ Nie udało się wysłać komunikatu o błędzie do użytkownika")

async def setup(bot: commands.Bot):
    await bot.add_cog(ocena(bot))