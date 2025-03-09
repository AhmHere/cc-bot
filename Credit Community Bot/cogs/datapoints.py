# cogs/credit_application.py
from os import name
from pydoc import text
import discord
from discord.ext import commands
from discord import app_commands

class StatusDropdown(discord.ui.Select):
    """Dropdown menu for selecting Approved or Denied before opening the modal"""

    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id
        options = [
            discord.SelectOption(label="✅ Approved", value="✅ Approved", description="Your application was approved"),
            discord.SelectOption(label="❌ Denied", value="❌ Denied", description="Your application was denied")
        ]
        super().__init__(placeholder="Select Application Status", options=options)

    async def callback(self, interaction: discord.Interaction):
        """Handles status selection and opens the first modal"""
        selected_status = self.values[0]
        await interaction.response.send_modal(CreditApplicationModal1(self.bot, self.user_id, selected_status))


class StatusDropdownView(discord.ui.View):
    """View for dropdown status selection"""

    def __init__(self, bot, user_id):
        super().__init__()
        self.add_item(StatusDropdown(bot, user_id))

class CreditApplicationModal1(discord.ui.Modal, title="Credit Card Datapoint - Part 1"):
    """First Modal for Credit Card DataPoints Submission"""

    credit_card_name = discord.ui.TextInput(label="Credit Card Name", required=True)
    credit_limit = discord.ui.TextInput(label="Credit Limit ($)", required=True)
    income = discord.ui.TextInput(label="Income ($)", required=True)
    credit_score = discord.ui.TextInput(label="Credit Score", required=True)

    def __init__(self, bot, user_id, status):
        super().__init__()
        self.bot = bot
        self.user_id = user_id
        self.status = status  # Store status from dropdown

    async def on_submit(self, interaction: discord.Interaction):
        """Handles first modal submission"""

        # Function to clean money inputs (remove $ and non-numeric characters)
        def clean_money(value):
            return ''.join(c for c in value if c.isdigit() or c == '.')

        # Store cleaned values in bot memory
        self.bot.user_modal_data[self.user_id] = {
            "Credit Card Name": self.credit_card_name.value,
            "Status": self.status,
            "Credit Limit": clean_money(self.credit_limit.value),
            "Income": clean_money(self.income.value),
            "Credit Score": self.credit_score.value
        }

        # Create button to transition to Modal 2
        view = OpenSecondModalView(self.bot, self.user_id)

        await interaction.response.send_message(
            "✅ Part 1 submitted!\nClick below to continue to the next step.",
            view=view,
            ephemeral=True
        )


class OpenSecondModalView(discord.ui.View):
    """View with a button to trigger the second modal"""

    def __init__(self, bot, user_id):
        super().__init__()
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="Continue to Part 2", style=discord.ButtonStyle.primary)
    async def open_second_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens the second modal when the button is clicked"""

        await interaction.response.send_modal(CreditApplicationModal2(self.bot, self.user_id))


class CreditApplicationModal2(discord.ui.Modal, title="Credit Card Datapoint - Part 2"):
    """Second Modal for Additional Details"""

    accounts = discord.ui.TextInput(label="Number of Accounts", required=True)
    x6accounts = discord.ui.TextInput(label="Accounts (Last 6 months)", required=True)
    x12accounts = discord.ui.TextInput(label="Accounts (Last 12 months)", required=True)
    x24accounts = discord.ui.TextInput(label="Accounts (Last 24 months)", required=True)
    aaoa = discord.ui.TextInput(label="Average Age of Accounts in # Years, # Months", required=True)

    def __init__(self, bot, user_id):
        super().__init__()
        self.bot = bot
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        """Handles second modal submission"""

        # Add new inputs to stored data
        self.bot.user_modal_data[self.user_id].update({
            "Accounts": self.accounts.value,
            "x/6 Accounts": self.x6accounts.value,
            "x/12 Accounts": self.x12accounts.value,
            "x/24 Accounts": self.x24accounts.value,
            "AAoA": self.aaoa.value,
        })

        # Create button to transition to Modal 3
        view = OpenThirdModalView(self.bot, self.user_id)

        await interaction.response.send_message(
            "✅ Part 2 submitted!\nClick below to continue to the final step.",
            view=view,
            ephemeral=True
        )


class OpenThirdModalView(discord.ui.View):
    """View with a button to trigger the third modal"""

    def __init__(self, bot, user_id):
        super().__init__()
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="Continue to Final Step", style=discord.ButtonStyle.success)
    async def open_third_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens the third modal when the button is clicked"""

        await interaction.response.send_modal(CreditApplicationModal3(self.bot, self.user_id))


class CreditApplicationModal3(discord.ui.Modal, title="Credit Card Datapoint - Part 3"):
    """Final Modal for Confirmation"""

    x6inquiries = discord.ui.TextInput(label="Inquiries (Last 6 months)", required=True)
    x12inquiries = discord.ui.TextInput(label="Inquiries (Last 12 months)", required=True)
    x24inquiries = discord.ui.TextInput(label="Inquiries (Last 24 months)", required=True)
    bureau_pulled = discord.ui.TextInput(label="Bureau Pulled (Experian, Equifax, or TU)", required=True)
    state = discord.ui.TextInput(label="State", required=True)

    def __init__(self, bot, user_id):
        super().__init__()
        self.bot = bot
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        """Handles final modal submission"""

        if self.user_id not in self.bot.user_modal_data:
            self.bot.user_modal_data[self.user_id] = {}

        # Add new inputs to stored data
        self.bot.user_modal_data[self.user_id].update({
            "x/6 Inquiries": self.x6inquiries.value,
            "x/12 Inquiries": self.x12inquiries.value,
            "x/24 Inquiries": self.x24inquiries.value,
            "Bureau Pulled": self.bureau_pulled.value,
            "State": self.state.value,
        })

        # Defer response first before sending the embed
        await interaction.response.defer()

        # Retrieve stored data
        data = self.bot.user_modal_data.pop(self.user_id, {})

        # Set embed color based on approval or denial
        embed_color = 0x00FF00 if data["Status"] == "✅ Approved" else 0xFF0000

        # Process the data points submission
        embed = discord.Embed(title="**Credit Card Data Points**", color=embed_color)

        embed.add_field(name="\n", value=f"**Credit Card Name:** {data['Credit Card Name']}", inline=False)
        embed.add_field(name="\n", value=f"**Status:** {'✅ Approved' if data['Status'] == '✅ Approved' else '❌ Denied'}", inline=False)
        embed.add_field(name="\n", value=f"**Credit Limit:** ${data['Credit Limit']}", inline=False)
        embed.add_field(name="\n", value=f"**Income:** ${data['Income']}", inline=False)
        embed.add_field(name="\n", value=f"**Credit Score:** {data['Credit Score']}", inline=False)
        embed.add_field(name="\n", value=f"**Number of Accounts:** {data['Accounts']}", inline=False)
        embed.add_field(name="\n", value=f"**New Accounts:** {data['x/6 Accounts']}/6, {data['x/12 Accounts']}/12, {data['x/24 Accounts']}/24", inline=False)
        embed.add_field(name="\n", value=f"**AAoA:** {data['AAoA']}", inline=False)
        embed.add_field(name="\n", value=f"**Bureau Pulled:** {self.bureau_pulled.value}", inline=False)
        embed.add_field(name="\n", value=f"**Inquiries:** {data['x/6 Inquiries']}/6, {data['x/12 Inquiries']}/12, {data['x/24 Inquiries']}/24", inline=False)
        embed.add_field(name="\n", value=f"**State:** {self.state.value}", inline=False)

        embed.set_footer(text=f"{interaction.user.display_name}", icon_url=interaction.user.avatar.url)

        # Send message using interaction.send_message() (after deferring)
        await interaction.followup.send(embed=embed)


class DataPointsCog(commands.Cog):
    """Handles the `/datapoints` command and modals"""

    def __init__(self, bot):
        self.bot = bot
        print("[DEBUG] DataPointsCog loaded – slash command should be registered.")
        self.bot.user_modal_data = {}

    @app_commands.command(name="datapoints", description="Submit your credit card application datapoints")
    async def datapoints(self, interaction: discord.Interaction):
        """Command to open the status selection dropdown"""
        view = StatusDropdownView(self.bot, interaction.user.id)
        await interaction.response.send_message("Select your application status:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DataPointsCog(bot))