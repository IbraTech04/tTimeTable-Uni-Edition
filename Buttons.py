import nextcord
from nextcord.ext import commands

class ConfirmDialogue(nextcord.ui.View):
    def init(self):
        super().init()
        self.value = None
    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green)
    async def confirm(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = True
        self.stop()
    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.red)
    async def deny(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.value = False
        self.stop()
        