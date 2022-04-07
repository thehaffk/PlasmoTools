import logging

import disnake
import requests
from disnake.ext import commands

import settings

logger = logging.getLogger(__name__)


class InterpolFunctions(commands.Cog):
    def __init__(self, bot):
        self.log_channel = None
        self.interpol_guild = None
        self.bot = bot

    @commands.has_role(settings.interpol["interpol"])
    @commands.slash_command(
        name="снять-штрафы-забаненным", guild_ids=[settings.interpol["id"]]
    )
    async def clear_penalties(self, inter: disnake.ApplicationCommandInteraction):

        """
        Пробегается по всем штрафам и снимает.

        Parameters
        inter: Inter
        """

        await inter.response.defer(ephemeral=True)
        counter = 0
        for tab in ["active", "check", "expired"]:
            penalties = requests.get(
                f"https://rp.plo.su/api/bank/penalties/helper?tab={tab}&from=0",
                cookies={"rp_token": settings.plasmo_token},
            ).json()
            if not penalties["status"]:
                return await inter.response.send_message(
                    f"Что-то пошло не так, не смог получить нормальный ответ от Plasmo",
                    ephemeral=True,
                )
            penalties = penalties["data"]

            for i in range(0, penalties["total"], 25):
                penalties = requests.get(
                    f"https://rp.plo.su/api/bank/penalties/helper?tab={tab}&from={i}",
                    cookies={"rp_token": settings.plasmo_token},
                ).json()["data"]["all"]["list"]
                for penalty in penalties:
                    try:
                        if requests.get(
                            f"https://rp.plo.su/api/user/profile"
                            f'?nick={penalty["user"]}'
                        ).json()["data"]["banned"]:
                            penalty_embed = disnake.Embed(
                                title="Штраф снят",
                                description=f'Штраф игроку [{penalty["user"]}](https://rp.plo.su/u/{penalty["user"]}), выданный {penalty["helper"]}, \
                            был снят системой автоматической отмены штрафов',
                                color=disnake.Color.red(),
                            )
                            penalty_embed.set_footer(
                                text="Проверку запустил " + inter.author.display_name,
                                icon_url=f"https://rp.plo.su/avatar/{inter.author.display_name}",
                            )

                            penalty_embed.add_field(
                                name="Информация о штрафе",
                                value=f'**ID**: {penalty["id"]} **Amount**: {penalty["amount"]} \n **Message**: \n {penalty["message"]}',
                            )

                            logger.info(
                                "Penalty canceled",
                                extra={
                                    "penalty": requests.delete(
                                        "https://rp.plo.su/api/bank/penalty",
                                        cookies={"rp_token": settings.plasmo_token},
                                        data={"penalty": penalty["id"]},
                                    ).json()
                                },
                            )
                            counter += 1

                            await self.log_channel.send(embed=penalty_embed)
                    except KeyError:
                        pass
                    except ConnectionError:
                        pass
        return await inter.edit_original_message(
            embed=disnake.Embed(
                title=f"Штрафов отменено: {counter}", color=disnake.Color.green()
            )
        )

    @commands.Cog.listener()
    async def on_ready(self):
        self.interpol_guild = self.bot.get_guild(settings.interpol["id"])
        self.log_channel = self.interpol_guild.get_channel(settings.interpol["logs"])
        logger.info("Ready")


def setup(client):
    client.add_cog(InterpolFunctions(client))
