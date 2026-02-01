import discord
import os
import datetime
import asyncio
import json
import aiofiles
import html
from cryptography.fernet import Fernet
from discord.ext import commands
from discord import ui, File
from discord.ext import tasks
from io import StringIO
from datetime import timezone
from zoneinfo import ZoneInfo  
import re
import cryptography
import aiohttp
import os


def add_employee_id(discord_id, nom_rp):
    try:
        with open("employes.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    
    for entry in data:
        if entry["id"] == discord_id:
            return

    data.append({"id": discord_id, "nom_rp": nom_rp})
    with open("employes.json", "w") as f:
        json.dump(data, f, indent=2)


intents = discord.Intents.all()
intents.messages = True
intents.reactions = True
intents.members = True
intents.message_content = True


def load_blacklist():
    try:
        with open('blacklist.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_blacklist(blacklist):
    with open('blacklist.json', 'w') as f:
        json.dump(blacklist, f, indent=2)

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


last_ticket_message = None


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


config = load_config()

CATEGORY_ID = config.get("category_id")
TEAM_ROLE_IDS = config.get("role_team_ids", [])
LOGS_CHANNEL_ID = config.get("logs_channel_id")
AUTO_ROLE_ID = config.get("auto_role_id")
PING_ROLE_ID = config.get("ping_role_id")


@bot.event
async def on_member_join(member):
    try:
        with open("blacklist.json", "r") as f:
            blacklist = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        blacklist = []

    if str(member.id) in blacklist:
        try:
            await member.send("Vous êtes blacklisté et ne pouvez pas rejoindre ce serveur.")
        except Exception:
            pass
        await member.kick(reason="Blacklist")
        print(f"Blacklist: {member} a été kick du serveur.")
        return

    config = load_config()
    auto_role_id = config.get("auto_role_id")
    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            try:
                await member.add_roles(role, reason="Attribution automatique à l'arrivée")
                print(f"Rôle {role.name} attribué à {member.name}")
            except discord.Forbidden:
                print("Permission refusée pour ajouter le rôle.")

    
def escape_html(text):
    import html
    return html.escape(text)

def format_discord_html(messages):
    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Transcript Discord</title>
        <style>
            body {
                background: #313338;
                color: #dbdee1;
                font-family: 'gg sans', 'Segoe UI', 'Arial', sans-serif;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 800px;
                margin: 30px auto;
                background: #2b2d31;
                border-radius: 8px;
                box-shadow: 0 2px 8px #0008;
                padding: 24px 0 24px 0;
            }
            .message {
                display: flex;
                align-items: flex-start;
                padding: 12px 32px;
                transition: background 0.2s;
            }
            .message:hover {
                background: #232428;
            }
            .avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                margin-right: 16px;
                flex-shrink: 0;
                border: 2px solid #232428;
            }
            .msg-content {
                flex: 1;
            }
            .header {
                display: flex;
                align-items: center;
                margin-bottom: 2px;
            }
            .author {
                font-weight: 600;
                margin-right: 8px;
                font-size: 15px;
            }
            .role-staff {
                color: #faa61a;
            }
            .role-admin {
                color: #ed4245;
            }
            .role-default {
                color: #dbdee1;
            }
            .timestamp {
                color: #949ba4;
                font-size: 12px;
                margin-left: 4px;
            }
            .content {
                font-size: 15px;
                line-height: 1.5;
                word-break: break-word;
            }
            .mention {
                background: #5865f2;
                color: #fff;
                border-radius: 3px;
                padding: 0 4px;
                font-size: 14px;
                margin: 0 2px;
            }
            .attachments img {
                max-width: 320px;
                margin-top: 8px;
                border-radius: 6px;
                box-shadow: 0 2px 8px #0006;
            }
            .embed {
                background: #23272a;
                border-left: 4px solid #5865f2;
                padding: 10px 16px;
                margin-top: 8px;
                border-radius: 6px;
                color: #fff;
            }
            .reactions {
                margin-top: 6px;
            }
            .reaction {
                display: inline-block;
                background: #383a40;
                border-radius: 12px;
                padding: 2px 8px;
                font-size: 14px;
                margin-right: 4px;
                color: #fff;
            }
        </style>
    </head>
    <body>
    <div class="container">
    <h2 style="text-align:center;color:#fff;margin-bottom:24px;">Transcript Discord</h2>
    """

    for message in messages:
        avatar_url = message.author.display_avatar.url
        author = escape_html(str(message.author.display_name))
        timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")

        if hasattr(message.author, "roles"):
            color_class = "role-default"
            for role in message.author.roles:
                if "admin" in role.name.lower():
                    color_class = "role-admin"
                elif "staff" in role.name.lower() or "mod" in role.name.lower():
                    color_class = "role-staff"
        else:
            color_class = "role-default"

        
        content = escape_html(message.content)
        url_pattern = r'(https?://\S+\.(?:png|jpg|jpeg|gif|webp))'
        def repl(match):
            url = match.group(1)
            return f'<br><img src="{url}" alt="Image" style="max-width:320px;margin-top:8px;border-radius:6px;box-shadow:0 2px 8px #0006;">'
        content = re.sub(url_pattern, repl, content)
        content = content.replace("\n", "<br>")

        html += f"""
        <div class="message">
            <img class="avatar" src="{avatar_url}">
            <div class="msg-content">
                <div class="header">
                    <span class="author {color_class}">{author}</span>
                    <span class="timestamp">{timestamp}</span>
                </div>
                <div class="content">{content}</div>
        """

        
        if message.embeds:
            for embed in message.embeds:
                title = escape_html(embed.title) if embed.title else ""
                desc = escape_html(embed.description) if embed.description else ""
                html += f'<div class="embed"><b>{title}</b><br>{desc}</div>'

        
        if message.attachments:
            html += '<div class="attachments">'
            for file in message.attachments:
                if file.url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    html += f'<img src="{file.url}" alt="Image" style="max-width:320px;margin-top:8px;border-radius:6px;box-shadow:0 2px 8px #0006;">'
                else:
                    html += f'<a href="{file.url}" style="color:#00b0f4;">{escape_html(file.filename)}</a>'
            html += '</div>'

        
        if message.reactions:
            html += '<div class="reactions">'
            for reaction in message.reactions:
                emoji = reaction.emoji
                count = reaction.count
                html += f'<span class="reaction">{emoji} {count}</span>'
            html += '</div>'

        html += "</div></div>"

    html += "</div></body></html>"
    return html

class CloseButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            ui.Button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
        )


class TicketButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @ui.button(label="📩 Contacter-nous", style=discord.ButtonStyle.blurple, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        author = interaction.user

        config = load_config()
        bl_role_id = config.get("bl_role_id")
        bl_role = guild.get_role(bl_role_id) if bl_role_id else None

        
        if bl_role and bl_role in author.roles:
            await interaction.followup.send("Vous êtes blacklisté et ne pouvez pas créer de ticket.", ephemeral=True)
            return

        ping_role_id = config.get("ping_role_id")
        ping_role = guild.get_role(ping_role_id) if ping_role_id else None

        
        formateur_role_id = config.get("role_formateur_id")
        formateur_role = guild.get_role(formateur_role_id) if formateur_role_id else None

        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{author.name.lower()}")
        if existing_channel:
            await interaction.response.send_message("Tu as déjà un ticket ouvert", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }

        
        for role_id in TEAM_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        
        if formateur_role:
            overwrites[formateur_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                add_reactions=True,
                manage_messages=True,
                read_message_history=True
            )
        hg_role_id = config.get("hg_role_id")
        if hg_role_id:
            hg_role = guild.get_role(hg_role_id)
            if hg_role:
                overwrites[hg_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    add_reactions=True,
                    manage_messages=True,
                    read_message_history=True
                )

        channel = await guild.create_text_channel(
            name=f"ticket-{author.name}",
            overwrites=overwrites,
            category=category,
            reason="Création de ticket via bouton"
        )

        mention = ""
        if ping_role:
            mention += ping_role.mention
        if formateur_role:
            mention += f" {formateur_role.mention}"

        await channel.send(
            f"{author.mention} {mention}",
            embed=discord.Embed(
                title="Ticket",
                description="Sélectionnez la catégorie de votre ticket",
                color=discord.Color.blurple()
            ),
            view=TicketTypeView(author)
        )

        await interaction.followup.send(f"Ticket créé {channel.mention}", ephemeral=True)


        async def auto_close():
            await asyncio.sleep(180)  

            current_channel = guild.get_channel(channel.id)
            if current_channel and current_channel.name.startswith("ticket-"):
                try:
                    await current_channel.send("Fermeture du ticket dans 5 secondes...")
                    await asyncio.sleep(5)
                    await current_channel.delete()
                except Exception as e:
                    print(f"[ERREUR auto_close] {e}")

        bot.loop.create_task(auto_close())



from discord.ext import tasks

last_ticket_message = None 

@tasks.loop(minutes=25)
async def send_ticket_reminder():
    global last_ticket_message

    await bot.wait_until_ready()
    config = load_config()
    channel_id = config.get("ticket_reminder_channel_id")

    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                
                if last_ticket_message:
                    try:
                        await last_ticket_message.delete()
                    except discord.NotFound:
                        pass  

                embed = discord.Embed(
                    title="Contacter la société 🚗",
                    description="Cliquer sur le bouton ci-dessous pour ouvrir un ticket",
                    color=discord.Color.yellow()
                )
                view = TicketButton()
                last_ticket_message = await channel.send(embed=embed, view=view)

                print("[INFO] Nouveau message ticket envoyé.")

            except Exception as e:
                print(f"[ERREUR] envoi du message ticket : {e}")
        else:
            print("❌ Channel introuvable")
    else:
        print("❌ ticket_reminder_channel_id manquant dans config.json")


class TicketTypeSelect(ui.Select):
    def __init__(self, author):
        self.author = author
        options = [
            discord.SelectOption(label="💼 Recrutement", value="⌛att-cv-", description="Postuler pour rejoindre la société"),
            discord.SelectOption(label="👮 Plainte", value="plainte", description="Déposer une plainte ou signalement sérieux"),
            discord.SelectOption(label="🔔 Autre", value="autre", description="Autre demande"),
            discord.SelectOption(label="💎 VIP", value="VIP", description="Devenir membre vip"),
        ]
        super().__init__(placeholder="Sélectionnez la catégorie du ticket", options=options, custom_id="ticket_type")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("Tu ne peux pas choisir le type de ticket d’un autre utilisateur.", ephemeral=True)
            return

        ticket_type = self.values[0]
        channel = interaction.channel
        guild = interaction.guild

        print(f"[DEBUG] Ticket type sélectionné : {ticket_type}")  

        new_name = f"{ticket_type}-{self.author.name}".lower().replace(" ", "-")
        try:
            await channel.edit(name=new_name)
        except Exception as e:
            print(f"❌ Erreur renommage : {e}")

        config = load_config()

        if ticket_type == "plainte":
            category_id = config.get("category_plainte_id")
        elif ticket_type == "autre":
            category_id = config.get("category_autre_id")
        elif ticket_type == "VIP":
            category_id = config.get("category_vip_id")
        else:
            category_id = config.get("category_id")

        if category_id:
            category = discord.utils.get(guild.categories, id=category_id)
            if category:
                try:
                    await channel.edit(category=category)
                except Exception as e:
                    print(f"❌ Erreur lors du déplacement dans la catégorie : {e}")

        try:
            if ticket_type == "⌛att-cv-":
                await channel.send(
                    f"Bonjour {self.author.mention},\n\n"
                    "Si tu souhaites rejoindre RoxWood Luxury Concessionnaire, je te laisse remplir ** [Le CV](https://docs.google.com/forms/d/1OwGJCFQTcfqbq3ajzrHOwsN_nfeo-ct7NVx2LFL-YTU/edit?ts=68f231a6) **"
                    "et nous envoyer ta candidature.\n\nN'oublie pas d'envoyer ta carte d'identité ainsi que ton permis, N'oublie pas de te renommer sur le serveur Nom & Prénom RP.\n\n*Cordialement*",
                    view=CloseButton()
                )
            elif ticket_type == "plainte":
                await channel.send(
                    f"Bonjour {self.author.mention},\n\n"
                    "Merci pour ta démarche. Décris-nous ta plainte de manière détaillée (lieu, date, personnes concernées...). "
                    "Un membre du staff prendra le relais rapidement.\n\n*Cordialement, l’équipe Haut Grader*",
                    view=CloseButton()
                )
            elif ticket_type == "autre":
                await channel.send(
                    f"{self.author.mention}, merci pour ta demande. Un membre de l'équipe va bientôt te répondre.",
                    view=CloseButton()
                )
            elif ticket_type == "VIP":
                embed = discord.Embed(
                    title="VIP",
                    description=f"{self.author.mention},\n\n"
                                "Création de votre dossier Membre VIP 💎\n"
                                "Merci de remplir ce formulaire pour créer votre carte membre vip.\n"
                                "⸻\n\n"
                                "👤 **Nom & Prénom RP :**\n→\n\n"
                                "🆔 **ID (FiveM) :**\n→\n\n"
                                "📅 **Date de la demande :**\n→\n\n"
                                "📞 **Numéro de téléphone RP :**\n→\n\n"
                                "📸 **Voulez-vous ajouter une photo ?** (facultatif)\n→\n\n"
                                "⸻\n\n"
                                "Un membre de notre équipe examinera votre demande et vous contactera bientôt.",
                    color=discord.Color.yellow()
                )
                await channel.send(embed=embed, view=CloseButton())
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi du message d'accueil : {e}")

        await interaction.message.delete()



class TicketTypeView(ui.View):
    def __init__(self, author):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect(author))


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") == "close_ticket":
        await interaction.response.send_message("📄 Génération du transcript...", ephemeral=True)

        messages = [message async for message in interaction.channel.history(limit=None, oldest_first=True)]

        html_content = format_discord_html(messages)
        buffer = StringIO(html_content)
        file = File(fp=buffer, filename="transcript.html")

        config = load_config()
        log_channel_id = config.get("logs_channel_id")
        log_channel = interaction.guild.get_channel(log_channel_id)

        if log_channel:
            await log_channel.send(f"Transcript du ticket {interaction.channel.name} :", file=file)
        else:
            await interaction.channel.send("Salon de logs introuvable dans la config")

        await interaction.channel.send("🔒 Fermeture du ticket dans 5 secondes...")
        await asyncio.sleep(5)
        await interaction.channel.delete()



@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx): 
    embed = discord.Embed(
        title="Contacter la société 🚗",
        description="Cliquer sur le bouton ci-dessous pour ouvrir un ticket",
        color=discord.Color.yellow()
    )
    view = TicketButton()
    await ctx.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    if ctx.channel.name.startswith("plainte-") or ctx.channel.name.startswith("⌛att-cv-") or ctx.channel.name.startswith("autre-") or ctx.channel.name.startswith("membre-vip-"):
        await ctx.send("Ticket fermé dans 5 secondes", delete_after=5)
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("Commande utilisable seulement dans un ticket", delete_after=5)


sniped_messages = {}
voice_state_updates = {}

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    sniped_messages[message.channel.id] = {
        "content": message.content,
        "author": str(message.author),
        "time": message.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

@bot.command()
async def snipe(ctx):
    snipe_data = sniped_messages.get(ctx.channel.id)
    if snipe_data:
        embed = discord.Embed(
            title="💬 Dernier message supprimé",
            description=snipe_data["content"],
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Auteur: {snipe_data['author']} • Envoyé à {snipe_data['time']}")
        await ctx.send(embed=embed)
    else:
        await ctx.send("Aucun message supprimé")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def rename(ctx, *, new_name: str):
    if ctx.channel.name.startswith("⌛att-cv-") or ctx.channel.name.startswith("plainte-") or ctx.channel.name.startswith("autre-") or ctx.channel.name.startswith("membre-vip-"):
        try:
            await ctx.channel.edit(name=new_name)
            await ctx.send(f"Nom du salon modifié : {new_name}", delete_after=5)
        except discord.Forbidden:
            await ctx.send("Je n'ai pas les permissions pour faire ça", delete_after=5)
        except discord.HTTPException:
            await ctx.send("Une erreur est survenue", delete_after=5)
    else:
        await ctx.send("Commande utilisable seulement dans un ticket", delete_after=5)
        

@bot.command()
@commands.has_permissions(administrator=True)
async def help(ctx):
    embed = discord.Embed(
        title="📘 Aide - Commandes disponibles",
        description="Voici la liste des commandes que tu peux utiliser :",
        color=discord.Color.blue()
    )
    embed.add_field(name="🧹 !clear", value="Supprime tous les messages du salon", inline=False)
    embed.add_field(name="🎟️ !ticket", value="Crée un ticket pour contacter la société", inline=False)
    embed.add_field(name="❌ !close", value="Ferme un ticket", inline=False)
    embed.add_field(name="🖋️ !rename", value="renome un ticket", inline=False)
    embed.add_field(name="⌛ !snipe", value="Voir le dernier message supprimé (ex. ghost ping)", inline=False)
    embed.add_field(name="⛔ !bl <id> <mention> ", value="Blacklist un utilisateur du discord (ne peut plus ouvrir de ticket)", inline=False)
    embed.add_field(name="🪙 !unbl <id> <mention> ", value="Unblacklist un utilisateur du discord", inline=False)
    embed.add_field(name="📝 !employes", value="Connaitre la liste des employés de l'entreprise", inline=False)
    embed.set_footer(text="Secrétaire - Roxwood Luxury Concessionnaire")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 1):
    """
    Supprime un nombre spécifié de messages (max 100)
    Utilisation: !clear [nombre=1]
    Exemple: !clear 10 (supprime 10 messages)
    """
    if amount <= 0:
        await ctx.send(" Veuillez spécifier un nombre supérieur à 0", delete_after=5)
        return
        
    if amount > 100:
        await ctx.send(" Le nombre de messages à supprimer ne peut pas dépasser 100", delete_after=5)
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f'✅ {len(deleted) - 1} message(s) supprimé(s)', delete_after=5)
        await asyncio.sleep(5)
        await msg.delete()
    except Exception as e:
        await ctx.send(f"Erreur lors de la suppression des messages: {e}", delete_after=5)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def bl(ctx, *, user_input: str = None):
    config = load_config()
    
    if not any(role.id in [int(rid) for rid in config.get('role_team_ids', [])] for role in ctx.author.roles):
        return await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")

    if not user_input:
        return await ctx.send("ℹ️ Utilisation: `!bl @utilisateur` ou `!bl ID_utilisateur`")

    target_id = None
    
    if ctx.message.mentions:
        target_id = str(ctx.message.mentions[0].id)
    else:
        import re
        match = re.search(r'\d+', user_input)
        if match:
            target_id = match.group(0)
        else:
            return await ctx.send("Veuillez mentionner un utilisateur ou fournir un ID valide.")
    
   
    blacklist = load_blacklist()

    if target_id not in blacklist:

        blacklist.append(target_id)
        save_blacklist(blacklist)
        
        try:
            member = await ctx.guild.fetch_member(int(target_id))
            if member:
                role = ctx.guild.get_role(int(config['bl_role_id']))
                if role:
                    await member.add_roles(role)
        except discord.NotFound:
            pass  
                
        await ctx.send(f"L'utilisateur <@{target_id}> a été ajouté à la blacklist.")
    else:
        await ctx.send(f"L'utilisateur <@{target_id}> est déjà dans la blacklist.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def unbl(ctx, *, user_input: str = None):
    config = load_config()
    
    if not any(role.id in [int(rid) for rid in config.get('role_team_ids', [])] for role in ctx.author.roles):
        return await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")
    if not user_input:
        return await ctx.send("ℹ️ Utilisation: `!unbl @utilisateur` ou `!unbl ID_utilisateur`")

    target_id = None
    
    if ctx.message.mentions:
        target_id = str(ctx.message.mentions[0].id)
    else:
        import re
        match = re.search(r'\d+', user_input)
        if match:
            target_id = match.group(0)
        else:
            return await ctx.send("Veuillez mentionner un utilisateur ou fournir un ID valide.")
    
    blacklist = load_blacklist()
    
    if target_id in blacklist:
        blacklist.remove(target_id)
        save_blacklist(blacklist)

        try:
            member = await ctx.guild.fetch_member(int(target_id))
            if member:
                role = ctx.guild.get_role(int(config['bl_role_id']))
                if role and role in member.roles:
                    await member.remove_roles(role)
        except discord.NotFound:
            pass  
                
        await ctx.send(f"Le joueur <@{target_id}> a été retiré de la blacklist.")
    else:
        await ctx.send(f"L'utilisateur <@{target_id}> n'est pas dans la blacklist.")


@bot.command()
@commands.has_permissions(administrator=True)
async def setlogschannel(ctx, log_type: str = None, channel: discord.TextChannel = None):
    """Définit le salon de logs pour différents types d'événements
    
    Types disponibles:
    - messages: Logs des messages supprimés/édités
    - roles: Logs des modifications de rôles
    - voice: Logs des activités vocales (entrée/sortie, mute, etc.)
    - boosts: Logs des boosts de serveur
    - all: Définit tous les types de logs sur le même salon
    """
    if not channel or not log_type or log_type.lower() not in ['messages', 'roles', 'voice', 'boosts', 'all']:
        await ctx.send("Utilisation: !setlogschannel <messages|roles|voice|boosts|all> #salon")
        return
        
    config = load_config()
    log_type = log_type.lower()
    
    if log_type in ['messages', 'all']:
        config['logs_messages_channel_id'] = str(channel.id)
    if log_type in ['roles', 'all']:
        config['logs_roles_channel_id'] = str(channel.id)
    if log_type in ['voice', 'all']:
        config['logs_voice_channel_id'] = str(channel.id)
    if log_type in ['boosts', 'all']:
        config['logs_boosts_channel_id'] = str(channel.id)
        
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
        
    await ctx.send(f"Salon de logs {log_type} défini sur {channel.mention}")
    
    global CONFIG
    CONFIG = config



@bot.command()
@commands.has_permissions(manage_messages=True)
async def employes(ctx):
    try:
        with open("employes.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    if not data:
        await ctx.send("Aucun employé enregistré.")
        return

    guild = ctx.guild
    entries = []
    for emp in data:
        member = guild.get_member(int(emp["id"]))
        mention = member.mention if member else "Inconnu"
        grade = emp.get("grade", "Inconnu")
        entries.append(f"**Grade:** {grade}\n**Mention:** {mention}")

    PAGE_SIZE = 6
    pages = [entries[i:i+PAGE_SIZE] for i in range(0, len(entries), PAGE_SIZE)]
    total_pages = len(pages)

    class EmployesView(ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.current_page = 0

        @ui.button(label="⬅️", style=discord.ButtonStyle.gray)
        async def prev(self, interaction: discord.Interaction, button: ui.Button):
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(embed=make_embed(self.current_page), view=self)
            else:
                await interaction.response.defer()

        @ui.button(label="➡️", style=discord.ButtonStyle.gray)
        async def next(self, interaction: discord.Interaction, button: ui.Button):
            if self.current_page < total_pages - 1:
                self.current_page += 1
                await interaction.response.edit_message(embed=make_embed(self.current_page), view=self)
            else:
                await interaction.response.defer()

    def make_embed(page):
        embed = discord.Embed(
            title=f"Employés ({page+1}/{total_pages})",
            description="\n\n".join(pages[page]),
            color=discord.Color.green()
        )
        return embed

    view = EmployesView()
    await ctx.send(embed=make_embed(0), view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def sync_employes(ctx):
    config = load_config()
    liaison_cat_id = config.get("employee_liaison_category_id")
    liaison_hg_cat_id = config.get("liaison_hg_category_id")
    categories = []
    cat1 = ctx.guild.get_channel(liaison_cat_id)
    cat2 = ctx.guild.get_channel(liaison_hg_cat_id)
    if cat1 and isinstance(cat1, discord.CategoryChannel):
        categories.append(cat1)
    if cat2 and isinstance(cat2, discord.CategoryChannel):
        categories.append(cat2)
    if not categories:
        await ctx.send("Aucune catégorie de liaison trouvée.")
        return

    employes = []
    for category in categories:
        for channel in category.text_channels:
            async for message in channel.history(limit=5, oldest_first=True):
                if message.mentions:
                    member = message.mentions[0]
                    employes.append({"id": str(member.id), "nom_rp": member.display_name})
                    break

    
    unique_employes = []
    ids_seen = set()
    for emp in employes:
        if emp["id"] not in ids_seen:
            unique_employes.append(emp)
            ids_seen.add(emp["id"])

    with open("employes.json", "w") as f:
        json.dump(unique_employes, f, indent=2)

    await ctx.send(f"{len(unique_employes)} employés synchronisés dans employes.json.")

@tasks.loop(minutes=1)
async def update_presence():
    if not bot.guilds:
        return
    guild = bot.guilds[0]
    member_count = guild.member_count

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{member_count} Citoyen(e)s"
    ))

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
        
    config = load_config()
    logs_channel = message.guild.get_channel(int(config.get('logs_messages_channel_id')))
    
    if not logs_channel:
        return
        
    embed = discord.Embed(
        title="Message supprimé",
        description=f"**Auteur:** {message.author.mention} (`{message.author.id}`)\n"
                  f"**Salon:** {message.channel.mention}\n"
                  f"**Contenu:**\n{message.content}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    file = discord.File("22c810830c50bfbf3de0f9f2c3125685.png", filename="logo.png")
    embed.set_thumbnail(url="attachment://logo.png")
    
    if message.attachments:
        files = []
        for attachment in message.attachments:
            files.append(f"- [{attachment.filename}]({attachment.proxy_url})")
        embed.add_field(name="Pièces jointes", value="\n".join(files), inline=False)
    
    embed.set_footer(text=f"ID du message: {message.id} | {message.guild.name}", icon_url=message.guild.icon.url if message.guild.icon else None)
    
    await logs_channel.send(embed=embed, file=file)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
        
    config = load_config()
    logs_channel_id = config.get('logs_messages_channel_id')
    if not logs_channel_id:
        return
        
    logs_channel = before.guild.get_channel(int(logs_channel_id))
    if not logs_channel:
        return
    embed = discord.Embed(
        title="Message édité",
        description=f"**Auteur:** {before.author.mention} (`{before.author.id}`)\n"
                  f"**Salon:** {before.channel.mention}\n"
                  f"**Ancien contenu:**\n{before.content}\n\n"
                  f"**Nouveau contenu:**\n{after.content}\n\n"
                  f"[Aller au message]({after.jump_url})",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    file = discord.File("22c810830c50bfbf3de0f9f2c3125685.png", filename="logo.png")
    embed.set_thumbnail(url="attachment://logo.png")
    
    embed.set_footer(text=f"ID du message: {before.id} | {before.guild.name}", icon_url=before.guild.icon.url if before.guild.icon else None)
    
    await logs_channel.send(embed=embed, file=file)
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    if not update_presence.is_running():
        update_presence.start()
    if not send_ticket_reminder.is_running():
        send_ticket_reminder.start()
    if not check_run_logs.is_running():
        check_run_logs.start()
    bot.add_view(TicketButton())

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas les permissions requises", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Utilisation : !clear <nombre>", delete_after=5)
    else:
        raise error
       
@bot.event
async def on_member_update(before, after):
    config = load_config()
    rwl_role_id = config.get("rwl_role_id")
    liaison_cat_id = config.get("employee_liaison_category_id")
    liaison_hg_cat_id = config.get("liaison_hg_category_id")
    guild = after.guild
    
    if before.premium_since is None and after.premium_since is not None:
        logs_channel_id = config.get("logs_boosts_channel_id")
        if logs_channel_id:
            logs_channel = after.guild.get_channel(int(logs_channel_id))
            if logs_channel:
                boost_count = after.guild.premium_subscription_count
                embed = discord.Embed(
                    title="✨ NOUVEAU BOOST SERVEUR",
                    description=f"**{after.mention}** a boosté le serveur !",
                    color=0xff73fa
                )
                embed.add_field(name="Niveau de boost", value=f"`Niveau {after.guild.premium_tier}`")
                embed.add_field(name="Nombre total de boosts", value=f"`{boost_count} boosts`")
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.timestamp = datetime.datetime.now()
                await logs_channel.send(embed=embed)
    
    if before.premium_since is not None and after.premium_since is None:
        logs_channel_id = config.get("logs_boosts_channel_id")
        if logs_channel_id:
            logs_channel = after.guild.get_channel(int(logs_channel_id))
            if logs_channel:
                boost_count = after.guild.premium_subscription_count
                embed = discord.Embed(
                    title="💔 FIN D'UN BOOST",
                    description=f"**{after.mention}** n'a pas renouvelé son boost.",
                    color=0x2f3136
                )
                embed.add_field(name="Niveau de boost", value=f"`Niveau {after.guild.premium_tier}`")
                embed.add_field(name="Nombre total de boosts", value=f"`{boost_count} boosts`")
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.timestamp = datetime.datetime.now()
                await logs_channel.send(embed=embed)
    
    if before.roles != after.roles:
        logs_channel_id = config.get("logs_roles_channel_id") or config.get("logs_messages_channel_id")
        if logs_channel_id:
            logs_channel = before.guild.get_channel(int(logs_channel_id))
            if logs_channel:
                before_roles = set(role.id for role in before.roles)
                after_roles = set(role.id for role in after.roles)
                
                added_roles = [role for role in after.roles if role.id not in before_roles]
                removed_roles = [role for role in before.roles if role.id not in after_roles]
                
                if added_roles or removed_roles:
  
                    moderator = None
                    try:
                        async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                            if entry.target.id == after.id and (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5:
                                moderator = entry.user
                                break
                    except Exception as e:
                        print(f"Erreur lors de la récupération des logs d'audit: {e}")
                    
                    embed = discord.Embed(
                        title="🔄 Modification de rôles",
                        description=f"**Membre:** {after.mention} (`{after.id}`)",
                        color=discord.Color.blue(),
                        timestamp=datetime.datetime.now(datetime.timezone.utc)
                    )
                    
                    if moderator:
                        embed.add_field(name="👤 Modérateur", value=f"{moderator.mention} (`{moderator.id}`)", inline=False)
                    
                    if added_roles:
                        roles_text = "\n".join([f"• {role.mention} (`{role.id}`)" for role in added_roles])
                        embed.add_field(name="🟢 Rôles ajoutés", value=roles_text, inline=False)
                        embed.color = discord.Color.green()
                    
                    if removed_roles:
                        roles_text = "\n".join([f"• {role.mention} (`{role.id}`)" for role in removed_roles])
                        embed.add_field(name="🔴 Rôles retirés", value=roles_text, inline=False)
                        embed.color = discord.Color.red()
                    
                    if added_roles and removed_roles:
                        embed.color = discord.Color.blue()
                    
                    try:
                        file = discord.File("22c810830c50bfbf3de0f9f2c3125685.png", filename="logo.png")
                        embed.set_thumbnail(url="attachment://logo.png")
                        
                        embed.set_footer(
                            text=f"ID du membre: {after.id} | {after.guild.name}",
                            icon_url=after.guild.icon.url if after.guild.icon else None
                        )
                        
                        await logs_channel.send(embed=embed, file=file)
                    except Exception as e:
                        print(f"Erreur lors de l'envoi du log de modification de rôles: {e}")
                        try:
                            await logs_channel.send(embed=embed)
                        except Exception as e2:
                            print(f"Échec de l'envoi du log: {e2}")
    grade_role_ids = [
        config.get("patron_id"),
        config.get("co_patron_id"),
        config.get("gerant_id"),
        config.get("manager_id"),
        config.get("vendeur_experimente_id"),
        config.get("vendeur_confirme_id"),
        config.get("vendeur_role_id"),
        config.get("stagiaire_role_id"),
    ]

    if rwl_role_id:
        role = guild.get_role(rwl_role_id)
        if role and role in before.roles and role not in after.roles:
            try:
                with open("employes.json", "r") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []
            new_data = [emp for emp in data if emp["id"] != str(after.id)]
            with open("employes.json", "w") as f:
                json.dump(new_data, f, indent=2)
            return

    
    if rwl_role_id and liaison_cat_id:
        role = guild.get_role(rwl_role_id)
        if role and role not in before.roles and role in after.roles:
            update_employee(after, config)
            add_employee_id(str(after.id), after.display_name)
            # category = guild.get_channel(liaison_cat_id)
            # if category and isinstance(category, discord.CategoryChannel):
            #     channel_name = f"{after.display_name.lower().replace(' ', '-')}"
            #     existing = discord.utils.get(category.text_channels, name=channel_name)
            #     if not existing:
            #         overwrites = {
            #             guild.default_role: discord.PermissionOverwrite(read_messages=False),
            #             after: discord.PermissionOverwrite(
            #                 read_messages=True,
            #                 send_messages=True,
            #                 attach_files=True,
            #                 add_reactions=True,
            #                 read_message_history=True
            #             ),
            #             guild.me: discord.PermissionOverwrite(
            #                 read_messages=True,
            #                 send_messages=True,
            #                 attach_files=True,
            #                 add_reactions=True,
            #                 manage_messages=True,
            #                 read_message_history=True
            #             )
            #         }
            #         formateur_role_id = config.get("role_formateur_id")
            #         hg_role_id = config.get("hg_role_id")
            #         if formateur_role_id:
            #             formateur_role = guild.get_role(formateur_role_id)
            #             if formateur_role:
            #                 overwrites[formateur_role] = discord.PermissionOverwrite(
            #                     read_messages=True,
            #                     send_messages=True,
            #                     attach_files=True,
            #                     add_reactions=True,
            #                     manage_messages=True,
            #                     read_message_history=True
            #                 )
            #         if hg_role_id:
            #             hg_role = guild.get_role(hg_role_id)
            #             if hg_role:
            #                 overwrites[hg_role] = discord.PermissionOverwrite(
            #                     read_messages=True,
            #                     send_messages=True,
            #                     attach_files=True,
            #                     add_reactions=True,
            #                     manage_messages=True,
            #                     read_message_history=True
            #                 )
            #         special_role = guild.get_role(1325960476039057409)
            #         if special_role:
            #             overwrites[special_role] = discord.PermissionOverwrite(
            #                 read_messages=True,
            #                 send_messages=True,
            #                 attach_files=True,
            #                 add_reactions=True,
            #                 manage_messages=True,
            #                 read_message_history=True
            #             )

            #         channel = await guild.create_text_channel(
            #             name=f"📁{after.display_name.lower().replace(' ', '-')}",
            #             category=category,
            #             overwrites=overwrites,
            #             reason="Nouveau employé RWL"
            #         )
            #         embed = discord.Embed(
            #             title=" Règlement Employé",
            #             description=(
            #                 "**- Respecter vos disponibilités.**\n"
            #                 "**- Être en tenue de service lorsque vous travaillez (à le mettre dans les vestiaires).**\n"
            #                 "**- Ne pas être AFK devant les clients. Retirer votre service et mettez vous en haut.**\n"
            #                 "**- Interdiction de faire du AFK FARM sous peine de sanctions.**\n"
            #                 "**- Pas de trash envers les clients/les collègues et les hauts gradés.**\n"
            #                 "**- Ne pas mettre de musique/tv au concessionnaire.**\n"
            #                 "**- Faire son quota OBLIGATOIRE qui est de 14H00 sinon pas de PAIE.**\n"
            #                 "**- Être en service minimum 2h00 par JOUR.**\n"
            #                 "**- Radio obligatoire quand vous êtes en service.**\n"
            #                 "**- Ne pas prendre + que vous prenez de vos repas/boissons journaliers.**\n"
            #                 "**- Avoir un vocabulaire correct (évitez de parler HRP ou du style au lieu de dire bonjour vous dites wesh...).**\n"
            #                 "**- Demander le permis de conduire et la carte identité (CI). Si c'est un véhicule orga demander que la CI mais si c'est personnel vous demandez les 2 documents dont le Permis et la CI. Si il l'a pas le permis pour le cas en personnel vous refusez la vente.**\n"
            #                 "**- Ne sautez pas sur les clients. Soyez mature chacun son tour et entraidez-vous, on est une EQUIPE !!!**\n"
            #                 "**- Quand vous êtes absent mettez dans le channel absence (réunion ou autre..).**\n"
            #                 "**- N'oubliez pas de mettre une annonce que le Concessionnaire est ouvert ou fermé. Bien sûr si vous êtes le dernier en service et que vous devez partir mettez l'annonce fermé.**\n"
            #                 "**- INTERDICTION DE FAIRE UN VEHICULE ENTREPRISE.**\n\n"
            #                 "---------------------------------------------\n"
            #                 "**Recensé auprès de la LSPD/BCSO**\n"
            #                 "**Casier judiciaire**\n"
            #                 "**Certificat d'aptitude du travail pour le concessionnaire**"
            #             ),
            #             color=discord.Color.blue()
            #         )
            #         embed.add_field(
            #             name="Liens Professionnels",
            #             value=(
            #                 "[Compta](https://concessrw.duckdns.org/account/login.php)\n"
            #             ),
            #             inline=False
            #         )
            #         await channel.send(embed=embed)
            #         ping_message = f"{after.mention}"
            #         await channel.send(ping_message)

    hg_role_id = config.get("hg_role_id")
    if hg_role_id and liaison_hg_cat_id:
        hg_role = guild.get_role(hg_role_id)
        if hg_role and hg_role not in before.roles and hg_role in after.roles:
            update_employee(after, config)
            add_employee_id(str(after.id), after.display_name)
            category = guild.get_channel(liaison_hg_cat_id)
            if category and isinstance(category, discord.CategoryChannel):
                channel_name = f"HG-{after.display_name.lower().replace(' ', '-')}"

                existing = discord.utils.get(category.text_channels, name=channel_name)
                if not existing:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        after: discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            add_reactions=True,
                            read_message_history=True
                        ),
                        guild.me: discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            add_reactions=True,
                            manage_messages=True,
                            read_message_history=True
                        )
                    }
                    channel = await guild.create_text_channel(
                        name=channel_name,
                        category=category,
                        overwrites=overwrites,
                        reason="Nouveau haut gradé"
                    )
                    embed = discord.Embed(
                        title=" Règlement Haut Gradé",
                        description=(
                            "**- Respectez les règles du serveur et du staff.**\n"
                            "**- Soyez exemplaire et aidez les nouveaux arrivants.**\n"
                            "**- Ne pas abuser des permissions qui vous sont données.**\n"
                            "**- Interdiction de faire du favoritisme.**\n"
                            "**- Gardez une attitude professionnelle en toute circonstance.**\n"
                            "**- En cas de problème, contactez un administrateur.**\n"
                            "**- Faites preuve de maturité et de discernement.**\n"
                            "**- Participez activement aux événements et à la vie du serveur.**\n"
                            "**- Respectez les décisions du staff, même si vous n'êtes pas d'accord.**\n"
                            "**- Ne divulguez pas d'informations sensibles concernant le serveur.**\n"
                            "**- Aidez à maintenir l'ordre et le respect dans toutes les interactions.**\n"
                            "**- Soyez un modèle pour les autres membres du serveur.**\n\n"
                            "---------------------------------------------\n"
                            "**Recensé auprès de la LSPD/BCSO**\n"
                            "**Casier judiciaire**\n"
                            "**Certificat d'aptitude du travail pour le concessionnaire**"
                        ),
                        color=discord.Color.green()
                    )
                    await channel.send(embed=embed)
                    ping_message = f"{after.mention}"
                    await channel.send(ping_message)

    for role_id in grade_role_ids:
        if not role_id:
            continue
        role = guild.get_role(role_id)
        if role and role not in before.roles and role in after.roles:
            update_employee(after, config)
            break
        if role and role in before.roles and role not in after.roles:
            update_employee(after, config)
            break

def get_member_grade(member, config):
    grade_roles = [
        ("Patron", config.get("patron_id")),
        ("Co-Patron", config.get("co_patron_id")),
        ("Gérant", config.get("gerant_id")),
        ("Manager", config.get("manager_id")),
        ("Vendeur Expérimenté", config.get("vendeur_experimente_id")),
        ("Vendeur Confirmé", config.get("vendeur_confirme_id")),
        ("Vendeur", config.get("vendeur_role_id")),
        ("Stagiaire", config.get("stagiaire_role_id")),
    ]
    for grade_name, role_id in grade_roles:
        if role_id and member.get_role(role_id):
            return grade_name
    return "Employé"

# Système de récupération des logs de runs
LOGS_RUN_CHANNEL_ID = 1365033396740559048  # Salon des logs de run
RUNS_CHANNEL_ID = 1467614639452979412      # Salon pour les messages des runs
run_summary_message_id = None  # ID du message récapitulatif
last_processed_date = None  # Date du dernier traitement

def get_week_start():
    """Retourne le lundi de la semaine en cours"""
    now = datetime.datetime.now(datetime.timezone.utc)
    # 0 = Monday, 6 = Sunday
    days_since_monday = now.weekday()
    week_start = now - datetime.timedelta(days=days_since_monday)
    # Mettre à minuit
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

def parse_sales_from_description(description):
    """Extrait le nom du vendeur et la quantité depuis la description"""
    try:
        import re
        
        if not description:
            return None, None
        
        seller_name = None
        quantity = None
        
        # Chercher la quantité (nombre avant 'x')
        # Ex: "Vente de 152x Siège Réparé..."
        match = re.search(r'(\d+)x', description)
        if match:
            quantity = int(match.group(1))
        
        # Chercher le vendeur après " par " (avec espaces pour éviter "Réparé")
        # Ex: "...pour 772$ par Oxy Narck. 1930$..."
        # IMPORTANT: chercher dans le lowercase mais extraire du ORIGINAL
        lower_desc = description.lower()
        if " par " in lower_desc:
            # Trouver l'index du dernier " par "
            last_par_index = lower_desc.rfind(" par ")
            if last_par_index != -1:
                # Extraire à partir du VRAI texte (pas le lowercase)
                after_par_original = description[last_par_index + 5:].strip()  # +5 = longueur de " par "
                # Enlever le point et tout ce qui vient après
                seller_name = after_par_original.split(".")[0].strip()
        
        print(f"[DEBUG] Parse - Description: '{description}' -> Vendeur: '{seller_name}', Quantité: {quantity}")
        return seller_name, quantity
    except Exception as e:
        print(f"Erreur lors du parsing: {e}")
        return None, None

@tasks.loop(minutes=10)
async def check_run_logs():
    """Récupère tous les messages de la semaine en cours et envoie un récapitulatif"""
    global run_summary_message_id, last_processed_date
    
    try:
        await bot.wait_until_ready()
        
        source_channel = bot.get_channel(LOGS_RUN_CHANNEL_ID)
        destination_channel = bot.get_channel(RUNS_CHANNEL_ID)
        
        if not source_channel or not destination_channel:
            print(f"[DEBUG] Canaux non trouvés")
            return
        
        week_start = get_week_start()
        print(f"[DEBUG] Récupération des messages depuis: {week_start}")
        
        sales_data = {}  # {vendeur: quantité}
        message_count = 0
        
        # Récupérer TOUS les messages de la semaine en cours
        async for message in source_channel.history(after=week_start):
            message_count += 1
            
            # Traiter chaque embed du message
            if message.embeds:
                for embed in message.embeds:
                    if embed.title == "Vente run" and embed.description:
                        seller_name, quantity = parse_sales_from_description(embed.description)
                        
                        if seller_name and quantity:
                            # Additionner les ventes
                            if seller_name in sales_data:
                                sales_data[seller_name] += quantity
                            else:
                                sales_data[seller_name] = quantity
                            print(f"[DEBUG] Vente enregistrée: {seller_name} -> {quantity}x")
        
        print(f"[DEBUG] {message_count} messages traités, {len(sales_data)} vendeurs trouvés")
        print(f"[DEBUG] Données de vente: {sales_data}")
        
        # Créer le message récapitulatif
        if sales_data:
            # Trier les vendeurs par quantité décroissante
            sorted_sales = sorted(sales_data.items(), key=lambda x: x[1], reverse=True)
            
            # Discord permet max 25 fields par embed, on limite et on affiche les autres en "Autres"
            MAX_FIELDS = 25
            main_vendors = sorted_sales[:MAX_FIELDS]
            other_vendors = sorted_sales[MAX_FIELDS:]
            
            summary_embed = discord.Embed(
                title="📊 Vente run",
                description="Retrouvez ci-dessous les ventes de la semaine",
                color=discord.Color.blue()
            )
            
            # Ajouter les vendeurs principaux
            for vendor, total_qty in main_vendors:
                summary_embed.add_field(
                    name=f"🚚 {vendor}",
                    value=f"{total_qty}x Siège Réparé",
                    inline=False
                )
            
            # Si plus de 25 vendeurs, ajouter un champ "Autres"
            if other_vendors:
                other_text = ", ".join([f"{v} ({q}x)" for v, q in other_vendors])
                summary_embed.add_field(
                    name="📝 Autres vendeurs",
                    value=other_text if len(other_text) < 1024 else other_text[:1021] + "... **Plus de 25 employés détéctés des erreurs peuvent survenir !**",
                    inline=False
                )
            
            summary_embed.set_footer(
                text=f"Mise à jour: {datetime.datetime.now(datetime.timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} | Total: {len(sales_data)} vendeurs"
            )
            
            # Créer ou modifier le message
            try:
                if run_summary_message_id:
                    try:
                        msg = await destination_channel.fetch_message(run_summary_message_id)
                        await msg.edit(embed=summary_embed)
                        print(f"[DEBUG] Message {run_summary_message_id} mis à jour")
                    except discord.NotFound:
                        # Le message n'existe plus, en créer un nouveau
                        new_msg = await destination_channel.send(embed=summary_embed)
                        run_summary_message_id = new_msg.id
                        print(f"[DEBUG] Nouveau message créé: {run_summary_message_id}")
                else:
                    # Créer un nouveau message
                    new_msg = await destination_channel.send(embed=summary_embed)
                    run_summary_message_id = new_msg.id
                    print(f"[DEBUG] Premier message créé: {run_summary_message_id}")
            except Exception as e:
                print(f"Erreur lors de l'envoi du message: {e}")
        else:
            print(f"[DEBUG] Aucune vente trouvée pour cette semaine")
    
    except Exception as e:
        print(f"Erreur dans check_run_logs: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    config = load_config()
    grade_channel_id = config.get("grade_channel_id")
    info_channel_id = config.get("channel_infoemployees_id")
    
    if message.channel.id == grade_channel_id:
        if message.author.bot:
            return

        pattern = r"<@&(\d+)>.*?:([\s\S]+?)(?:\n|$)"
        matches = re.findall(pattern, message.content)

        if not matches:
            return

        success = 0
        failed = 0
        for role_id, users_str in matches:
            user_ids = re.findall(r"<@!?(\d+)>", users_str)
            role = message.guild.get_role(int(role_id))
            for user_id in user_ids:
                member = message.guild.get_member(int(user_id))
                if role and member:
                    try:
                        await member.add_roles(role, reason="Montée de grade automatique (auto-event)")
                        success += 1
                    except Exception:
                        failed += 1
                else:
                    failed += 1

    
    if message.channel.id == info_channel_id and not message.author.bot:
        
        template_regex = (
            r"𝐍𝐨𝐦 𝐄𝐭 𝐏𝐫𝐞𝐧𝐨𝐦(?:\s*👤)?\s*:?\s*(.+)\n"
            r"𝐈𝐃 𝐮𝐧𝐢𝐪𝐮𝐞(?:\s*🆔)?\s*:?\s*(.+)\n"
            r"𝐍𝐮𝐦𝐞́𝐫𝐨 𝐝𝐞 𝐭𝐞́𝐥𝐥𝐞́𝐩𝐡𝐨𝐧𝐞(?:\s*📞)?\s*:?\s*(.+)\n"
            r"𝐂𝐚𝐫𝐭𝐞 𝐃’𝐢𝐝𝐞𝐧𝐭𝐢𝐭𝐞́(?:\s*🪪)?\s*:?"
        )
        match = re.search(template_regex, message.content)
        if match:
            nom_prenom = match.group(1).strip()
            id_unique = match.group(2).strip()
            tel = match.group(3).strip()
            image_url = None
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                        image_url = attachment.url
                        break
            if not image_url:
                await message.channel.send(
                    f"{message.author.mention} Merci de joindre une image de la carte d'identité en pièce jointe !",
                    delete_after=10
                )
                return

            embed = discord.Embed(
                title="Fiche employé",
                color=discord.Color.green()
            )
            embed.add_field(name="👤 Nom et Prénom", value=nom_prenom, inline=False)
            embed.add_field(name="🆔 ID unique", value=id_unique, inline=False)
            embed.add_field(name="📞 Numéro de téléphone", value=tel, inline=False)
            embed.set_footer(text=f"Ajouté par {message.author.display_name}")
            embed.set_image(url=image_url)

            await message.channel.send(f"{message.author.mention}", embed=embed)
            await asyncio.sleep(1)
            try:
                await message.delete()
            except discord.NotFound:
                pass
            
    await bot.process_commands(message)


def update_employee(member, config):
    try:
        with open("employes.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    grade = get_member_grade(member, config)
    discord_id = str(member.id)
    nom_rp = member.display_name

    if grade == "Employé":
        new_data = [emp for emp in data if emp["id"] != discord_id]
        with open("employes.json", "w") as f:
            json.dump(new_data, f, indent=2)
        return

    found = False
    for entry in data:
        if entry["id"] == discord_id:
            entry["nom_rp"] = nom_rp
            entry["grade"] = grade
            found = True
            break
    if not found:
        data.append({"id": discord_id, "nom_rp": nom_rp, "grade": grade})

    grade_order = [
        "Patron", "Co-Patron", "Gérant", "Manager",
        "Vendeur Expérimenté", "Vendeur Confirmé", "Vendeur", "Stagiaire"
    ]
    data.sort(key=lambda x: grade_order.index(x["grade"]) if x["grade"] in grade_order else len(grade_order))

    with open("employes.json", "w") as f:
        json.dump(data, f, indent=2)




@bot.event
async def on_member_join(member):
    try:
        role = member.guild.get_role(1320808684443668500)
        if role:
            await member.add_roles(role, reason="Attribution automatique du rôle à l'arrivée")
    except Exception as e:
        print(f"Erreur lors de l'ajout du rôle au nouveau membre: {e}")
    
    blacklist = load_blacklist()
    if str(member.id) in blacklist:
        role = member.guild.get_role(int(config['bl_role_id']))
        if role:
            await member.add_roles(role)
            print(f"Rôle blacklist appliqué à {member.name} (ID: {member.id})")

@bot.command()
@commands.has_permissions(mute_members=True)
async def vmute(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    """Mute un membre en vocal"""
    if member.voice is None:
        return await ctx.send("Ce membre n'est pas dans un salon vocal.")
    
    if member.voice.mute:
        return await ctx.send("Ce membre est déjà mute.")
    
    try:
        await member.edit(mute=True, reason=f"Par {ctx.author} (ID: {ctx.author.id}): {reason}")
        voice_state_updates[member.id] = {
            "moderator_id": ctx.author.id,
            "moderator_name": str(ctx.author),
            "action": "mute",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
        }
        await ctx.send(f"🔇 {member.mention} a été mute en vocal par {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Erreur lors du mute: {e}")

@bot.command()
@commands.has_permissions(mute_members=True)
async def vunmute(ctx, member: discord.Member):
    """Démute un membre en vocal"""
    if member.voice is None:
        return await ctx.send("Ce membre n'est pas dans un salon vocal.")
    
    if not member.voice.mute:
        return await ctx.send("Ce membre n'est pas mute.")
    
    try:
        await member.edit(mute=False, reason=f"Démute par {ctx.author} (ID: {ctx.author.id})")
        voice_state_updates[member.id] = {
            "moderator_id": ctx.author.id,
            "moderator_name": str(ctx.author),
            "action": "unmute",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
        }
        await ctx.send(f"🔊 {member.mention} a été démuté en vocal par {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Erreur lors du démute: {e}")

@bot.command()
@commands.has_permissions(deafen_members=True)
async def vdeaf(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):
    """Sourdine un membre en vocal"""
    if member.voice is None:
        return await ctx.send("Ce membre n'est pas dans un salon vocal.")
    
    if member.voice.deaf:
        return await ctx.send("Ce membre est déjà en sourdine.")
    
    try:
        await member.edit(deafen=True, reason=f"Par {ctx.author} (ID: {ctx.author.id}): {reason}")
        voice_state_updates[member.id] = {
            "moderator_id": ctx.author.id,
            "moderator_name": str(ctx.author),
            "action": "deaf",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
        }
        await ctx.send(f"🔇 {member.mention} a été mis en sourdine par {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Erreur lors de la mise en sourdine: {e}")

@bot.command()
@commands.has_permissions(deafen_members=True)
async def vundeaf(ctx, member: discord.Member):
    """Retire la sourdine d'un membre en vocal"""
    if member.voice is None:
        return await ctx.send("Ce membre n'est pas dans un salon vocal.")
    
    if not member.voice.deaf:
        return await ctx.send("Ce membre n'est pas en sourdine.")
    
    try:
        await member.edit(deafen=False, reason=f"Retrait de la sourdine par {ctx.author} (ID: {ctx.author.id})")
        voice_state_updates[member.id] = {
            "moderator_id": ctx.author.id,
            "moderator_name": str(ctx.author),
            "action": "undeaf",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).timestamp()
        }
        await ctx.send(f"🔊 {member.mention} n'est plus en sourdine (par {ctx.author.mention}).")
    except Exception as e:
        await ctx.send(f"Erreur lors du retrait de la sourdine: {e}")

async def get_moderator_from_audit_log(guild, target_member, action_type):
    """Récupère le modérateur depuis les logs d'audit"""
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
            if (entry.target.id == target_member.id and 
                (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 10):
                
                if hasattr(entry.after, 'mute') and entry.after.mute == (action_type == 'mute'):
                    return entry.user
                if hasattr(entry.after, 'deaf') and entry.after.deaf == (action_type == 'deaf'):
                    return entry.user
                if hasattr(entry.before, 'deaf') and entry.before.deaf and not entry.after.deaf and action_type == 'undeaf':
                    return entry.user
    except Exception as e:
        print(f"Erreur lors de la récupération des logs d'audit: {e}")
    return None

@bot.event
async def on_voice_state_update(member, before, after):
    """Gère les logs pour les changements d'état vocal"""
    config = load_config()
    logs_channel_id = config.get('logs_voice_channel_id')
    
    if not logs_channel_id:
        return
        
    logs_channel = member.guild.get_channel(int(logs_channel_id))
    if not logs_channel:
        return
    
    embed = discord.Embed(
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    if before.channel != after.channel:
        moderator = None
        action = None
        
        try:
            async for entry in member.guild.audit_logs(limit=5):
                if not hasattr(entry, 'action') or not hasattr(entry, 'target') or not entry.target:
                    continue
                if (hasattr(entry.target, 'id') and entry.target.id == member.id and 
                    (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5):
                    if entry.action == discord.AuditLogAction.member_disconnect:
                        if hasattr(entry, 'user') and entry.user:
                            moderator = entry.user
                            action = 'kick'
                            break
                            
                    elif entry.action == discord.AuditLogAction.member_move:
                        if hasattr(entry, 'user') and entry.user and entry.user.id != member.id:
                            moderator = entry.user
                            action = 'move'
                            break
                            
                    elif entry.action == discord.AuditLogAction.member_update and before.channel and not after.channel:
                        if hasattr(entry, 'user') and entry.user and entry.user.id != member.id:
                            moderator = entry.user
                            action = 'disconnect'
                            break
                            
        except Exception as e:
            print(f"Erreur lors de la vérification des logs d'audit: {e}")
        except Exception as e:
            print(f"Erreur lors de la vérification du déplacement: {e}")
        
        if not before.channel and after.channel:
            embed.title = "🔊 Entrée en vocal"
            embed.color = discord.Color.blue()
            embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
            embed.add_field(name="Salon", value=after.channel.mention, inline=True)
            
        elif before.channel and not after.channel:
            if action == 'kick' and moderator:
                embed.title = "🔴 Kick vocal"
                embed.color = discord.Color.red()
                embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
                embed.add_field(name="Modérateur", value=f"{moderator.mention}", inline=False)
                embed.add_field(name="Salon", value=before.channel.mention, inline=True)
                
            elif action == 'disconnect' and moderator:
                embed.title = "🔌 Déconnexion forcée"
                embed.color = discord.Color.dark_red()
                embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
                embed.add_field(name="Modérateur", value=f"{moderator.mention}", inline=False)
                embed.add_field(name="Salon", value=before.channel.mention, inline=True)
                
            else:
                embed.title = "🚪 Sortie de vocal"
                embed.color = discord.Color.from_rgb(255, 105, 180)
                embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
                embed.add_field(name="Salon quitté", value=before.channel.mention, inline=True)
            
        else:
            if action == 'move' and moderator:
                embed.title = "🚚 Déplacement vocal"
                embed.color = discord.Color.orange()
                embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
                embed.add_field(name="Modérateur", value=f"{moderator.mention}", inline=False)
                embed.add_field(name="Ancien salon", value=before.channel.mention, inline=True)
                embed.add_field(name="Nouveau salon", value=after.channel.mention, inline=True)
            else:
                embed.title = "🔄 Changement de salon vocal"
                embed.color = discord.Color.blue()
            
            embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
            embed.add_field(name="Ancien salon", value=before.channel.mention, inline=True)
            embed.add_field(name="Nouveau salon", value=after.channel.mention, inline=True)
    
    elif before.self_mute != after.self_mute:
        if after.self_mute:
            embed.title = "🔇 Auto-mute activé"
            embed.color = discord.Color.red()
        else:
            embed.title = "🔊 Auto-mute désactivé"
            embed.color = discord.Color.green()
        embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
        embed.add_field(name="Salon", value=after.channel.mention if after.channel else "Inconnu", inline=True)
    
    elif before.self_deaf != after.self_deaf:
        if after.self_deaf:
            embed.title = "🔇 Auto-sourdine activée"
            embed.color = discord.Color.red()
        else:
            embed.title = "🔊 Auto-sourdine désactivée"
            embed.color = discord.Color.green()
        embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
        embed.add_field(name="Salon", value=after.channel.mention if after.channel else "Inconnu", inline=True)
    
    elif before.mute != after.mute:
        moderator = None
        
        if after.mute:
            action = "mute"
            embed.title = "🔇 Mute par un modérateur"
            embed.color = discord.Color.orange()
            moderator_info = voice_state_updates.get(member.id, {})
            if moderator_info.get('action') == 'mute':
                moderator = member.guild.get_member(moderator_info.get('moderator_id'))
            
            if not moderator:
                moderator = await get_moderator_from_audit_log(member.guild, member, 'mute')
        else:
            action = "unmute"
            embed.title = "🔊 Démute par un modérateur"
            embed.color = discord.Color.green()
            moderator_info = voice_state_updates.get(member.id, {})
            if moderator_info.get('action') == 'unmute':
                moderator = member.guild.get_member(moderator_info.get('moderator_id'))
            
            if not moderator:
                moderator = await get_moderator_from_audit_log(member.guild, member, 'unmute')
        
        embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
        
        if moderator:
            embed.add_field(name="Modérateur", value=f"{moderator.mention} ({moderator.name}#{moderator.discriminator})", inline=False)
        else:
            embed.add_field(name="Modérateur", value="Inconnu (peut-être un bot ou une action manuelle)", inline=False)
            
        embed.add_field(name="Salon", value=after.channel.mention if after.channel else "Inconnu", inline=True)
        
        if member.id in voice_state_updates:
            if (voice_state_updates[member.id]['action'] == action and 
                (datetime.datetime.now(datetime.timezone.utc).timestamp() - voice_state_updates[member.id]['timestamp']) < 5):
                del voice_state_updates[member.id]
    
    elif before.deaf != after.deaf:
        moderator = None
        
        if after.deaf:
            action = "deaf"
            embed.title = "🔇 Sourdine par un modérateur"
            embed.color = discord.Color.orange()
            moderator_info = voice_state_updates.get(member.id, {})
            if moderator_info.get('action') == 'deaf':
                moderator = member.guild.get_member(moderator_info.get('moderator_id'))
            if not moderator:
                moderator = await get_moderator_from_audit_log(member.guild, member, 'deaf')
        else:
            action = "undeaf"
            embed.title = "🔊 Désactivation de la sourdine par un modérateur"
            embed.color = discord.Color.green()
            moderator_info = voice_state_updates.get(member.id, {})
            if moderator_info.get('action') == 'undeaf':
                moderator = member.guild.get_member(moderator_info.get('moderator_id'))
            if not moderator:
                moderator = await get_moderator_from_audit_log(member.guild, member, 'undeaf')
        
        embed.description = f"**Membre:** {member.mention} (`{member.id}`)"
        
        if moderator:
            embed.add_field(name="Modérateur", value=f"{moderator.mention} ({moderator.name}#{moderator.discriminator})", inline=False)
        else:
            embed.add_field(name="Modérateur", value="Inconnu (peut-être un bot ou une action manuelle)", inline=False)
            
        embed.add_field(name="Salon", value=after.channel.mention if after.channel else "Inconnu", inline=True)
        
        if member.id in voice_state_updates:
            if (voice_state_updates[member.id]['action'] == action and 
                (datetime.datetime.now(datetime.timezone.utc).timestamp() - voice_state_updates[member.id]['timestamp']) < 5):
                del voice_state_updates[member.id]
    
    else:
        return
    
    try:
        file = discord.File("22c810830c50bfbf3de0f9f2c3125685.png", filename="logo.png")
        embed.set_thumbnail(url="attachment://logo.png")
        embed.set_footer(
            text=f"ID: {member.id} | {member.guild.name}",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        await logs_channel.send(embed=embed, file=file)
    except Exception as e:
        print(f"Erreur lors de l'envoi du log vocal: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def blstat(ctx):
    """Affiche la liste des utilisateurs blacklistés avec pagination"""
    blacklist = load_blacklist()
    if not blacklist:
        await ctx.send("Aucun utilisateur n'est actuellement blacklisté.")
        return
    
    entries = []
    for user_id in blacklist:
        try:
            user = await bot.fetch_user(int(user_id))
            mention = f"{user.mention} ({user.name}#{user.discriminator})"
        except discord.NotFound:
            mention = f"ID inconnu: {user_id}"
        entries.append(f"**ID:** `{user_id}`\n**Utilisateur:** {mention}")
    
    PAGE_SIZE = 5
    pages = [entries[i:i + PAGE_SIZE] for i in range(0, len(entries), PAGE_SIZE)]
    total_pages = len(pages)
    
    embed = discord.Embed(
        title=f"Liste des utilisateurs blacklistés (1/{total_pages})",
        description="\n\n".join(pages[0]) if pages[0] else "Aucun utilisateur blacklisté",
        color=discord.Color.red()
    )
    
    class PaginationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)
            self.current_page = 0
            self.total_pages = total_pages
            self.entries = pages
        
        async def update_embed(self, interaction):
            self.current_page %= self.total_pages
            
            embed = discord.Embed(
                title=f"Liste des utilisateurs blacklistés ({self.current_page + 1}/{self.total_pages})",
                description="\n\n".join(self.entries[self.current_page]),
                color=discord.Color.red()
            )
            
            self.children[0].disabled = self.current_page == 0
            self.children[1].disabled = self.current_page >= self.total_pages - 1
            
            await interaction.response.edit_message(embed=embed, view=self)
        
        @discord.ui.button(label="⬅️ Précédent", style=discord.ButtonStyle.primary, disabled=True)
        async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page -= 1
            await self.update_embed(interaction)
        
        @discord.ui.button(label="Suivant ➡️", style=discord.ButtonStyle.primary)
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page += 1
            await self.update_embed(interaction)
    
    view = PaginationView()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def testboost(ctx):
    """Affiche un aperçu des messages de logs pour les boosts"""
    config = load_config()
    logs_channel_id = config.get("logs_boosts_channel_id")
    
    if not logs_channel_id:
        return await ctx.send("Aucun salon de logs pour les boosts n'est configuré. Utilisez `!setlogschannel boosts #salon` pour en définir un.")
    
    logs_channel = ctx.guild.get_channel(int(logs_channel_id))
    if not logs_channel:
        return await ctx.send("Le salon de logs pour les boosts est introuvable.")
    
    new_boost_embed = discord.Embed(
        title="✨ NOUVEAU BOOST SERVEUR (TEST)",
        description=f"**{ctx.author.mention}** a boosté le serveur ! (TEST)",
        color=0xff73fa
    )
    new_boost_embed.add_field(name="Niveau de boost", value=f"`Niveau {ctx.guild.premium_tier}`")
    new_boost_embed.add_field(name="Nombre total de boosts", value=f"`{ctx.guild.premium_subscription_count} boosts`")
    new_boost_embed.set_thumbnail(url=ctx.author.display_avatar.url)
    new_boost_embed.timestamp = datetime.datetime.now()
    
    end_boost_embed = discord.Embed(
        title="💔 FIN D'UN BOOST (TEST)",
        description=f"**{ctx.author.mention}** n'a pas renouvelé son boost. (TEST)",
        color=0x2f3136
    )
    end_boost_embed.add_field(name="Niveau de boost", value=f"`Niveau {ctx.guild.premium_tier}`")
    end_boost_boost_count = max(0, ctx.guild.premium_subscription_count - 1)
    end_boost_embed.add_field(name="Nombre total de boosts", value=f"`{end_boost_boost_count} boosts`")
    end_boost_embed.set_thumbnail(url=ctx.author.display_avatar.url)
    end_boost_embed.timestamp = datetime.datetime.now()
    
    await logs_channel.send(embed=new_boost_embed)
    await logs_channel.send(embed=end_boost_embed)
    
    await ctx.send(f"Messages de test envoyés dans {logs_channel.mention}")


with open("secret.key", "rb") as key_file:
    key = key_file.read()


with open(".env.crypt", "rb") as f:
    encrypted_token = f.read()


fernet = Fernet(key)
decrypted_token = fernet.decrypt(encrypted_token).decode()

bot.run(decrypted_token)
