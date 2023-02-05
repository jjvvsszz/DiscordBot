import discord
from discord import app_commands
from src import responses
from src import log

logger = log.setup_logger(__name__)

config = responses.get_config()

isPrivate = False


class aclient(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.activity = discord.Activity(type=discord.ActivityType.watching, name="/conversar | discord.gg/falon")


async def send_message(message, user_message):
    await message.response.defer(ephemeral=isPrivate)
    try:
        response = '> **' + user_message + '** - <@' + \
            str(message.user.id) + '> \n\n'
        response = f"{response}{await responses.handle_response(user_message)}"
        if len(response) > 1900:
            # Split the response into smaller chunks of no more than 1900 characters each(Discord limit is 2000 per chunk)
            if "```" in response:
                # Split the response if the code block exists
                parts = response.split("```")
                # Send the first message
                await message.followup.send(parts[0])
                # Send the code block in a seperate message
                code_block = parts[1].split("\n")
                formatted_code_block = ""
                for line in code_block:
                    while len(line) > 1900:
                        # Split the line at the 50th character
                        formatted_code_block += line[:1900] + "\n"
                        line = line[1900:]
                    formatted_code_block += line + "\n"  # Add the line and seperate with new line

                # Send the code block in a separate message
                if (len(formatted_code_block) > 2000):
                    code_block_chunks = [formatted_code_block[i:i+1900]
                                         for i in range(0, len(formatted_code_block), 1900)]
                    for chunk in code_block_chunks:
                        await message.followup.send("```" + chunk + "```")
                else:
                    await message.followup.send("```" + formatted_code_block + "```")

                # Send the remaining of the response in another message

                if len(parts) >= 3:
                    await message.followup.send(parts[2])
            else:
                response_chunks = [response[i:i+1900]
                                   for i in range(0, len(response), 1900)]
                for chunk in response_chunks:
                    await message.followup.send(chunk)
        else:
            await message.followup.send(response)
    except Exception as e:
        await message.followup.send("> **Erro: Algo deu errado, tente novamente mais tarde!**")
        logger.exception(f"Erro ao enviar mensagem: {e}")


async def send_start_prompt(client):
    import os
    import os.path

    config_dir = os.path.abspath(__file__ + "/../../")
    prompt_name = 'starting-prompt.txt'
    prompt_path = os.path.join(config_dir, prompt_name)
    try:
        if os.path.isfile(prompt_path) and os.path.getsize(prompt_path) > 0:
            with open(prompt_path, "r") as f:
                prompt = f.read()
                if (config['discord_channel_id']):
                    logger.info(f"Enviar prompt inicial com tamanho {len(prompt)}")
                    responseMessage = await responses.handle_response(prompt)
                    channel = client.get_channel(int(config['discord_channel_id']))
                    await channel.send(responseMessage)
                    logger.info(f"Iniciando a resposta imediata:{responseMessage}")
                else:
                    logger.info("Nenhum canal selecionado. Ignore o envio do prompt inicial.")
        else:
            logger.info(f"No {prompt_name}. Ignore o envio do prompt inicial.")
    except Exception as e:
        logger.exception(f"Erro ao enviar o prompt inicial: {e}")


def run_discord_bot():
    client = aclient()

    @client.event
    async def on_ready():
        await send_start_prompt(client)
        await client.tree.sync()
        logger.info(f'{client.user} Agora está em execução!')

    @client.tree.command(name="conversar", description="Converse com a IA")
    async def conversar(interaction: discord.Interaction, *, message: str):
        username = str(interaction.user)
        user_message = message
        channel = str(interaction.channel)
        logger.info(
            f"\x1b[31m{username}\x1b[0m : '{user_message}' ({channel})")
        embed = discord.Embed(
        title=f"{username} pergunta:",
        description=f"{user_message}\n\nResposta: {interaction}"
        )
        await send_message(interaction, user_message)
        #await interaction.channel.send(embed=embed)

    @client.tree.command(name="privado", description="Alternar acesso privado")
    async def privado(interaction: discord.Interaction):
        global isPrivate
        await interaction.response.defer(ephemeral=False)
        if not isPrivate:
            isPrivate = not isPrivate
            logger.warning("\x1b[31mAlternar acesso privado\x1b[0m")
            await interaction.followup.send("> **Informação: A seguir, a resposta será enviada por mensagem privada. Se você quiser voltar ao modo público, use `/publico`**")
        else:
            logger.info("Você já está no modo privado!")
            await interaction.followup.send("> **Aviso: Você já está no modo privado. Se você quiser mudar para o modo público, use `/publico`**")

    @client.tree.command(name="publico", description="Alternar acesso público")
    async def publico(interaction: discord.Interaction):
        global isPrivate
        await interaction.response.defer(ephemeral=False)
        if isPrivate:
            isPrivate = not isPrivate
            await interaction.followup.send("> **Info: Em seguida, a resposta será enviada diretamente para o canal. Se você quiser voltar ao modo privado, use `/privado`**")
            logger.warning("\x1b[31mAlternar para o modo público\x1b[0m")
        else:
            await interaction.followup.send("> **Aviso: Você já está em modo público. Se você quiser mudar para o modo privado, use `/privado`**")
            logger.info("Você já está em modo público!")

    @client.tree.command(name="apagar", description="Conclua a redefinição do histórico de conversas do ChatGPT")
    async def apagar(interaction: discord.Interaction):
        responses.chatbot.reset()
        await interaction.response.defer(ephemeral=False)
        await interaction.followup.send("> **Info: Eu esqueci tudo.**")
        logger.warning(
            "\x1b[31mO bot ChatGPT foi redefinido com sucesso\x1b[0m")
        await send_start_prompt(client)


    TOKEN = config['discord_bot_token']
    client.run(TOKEN)
