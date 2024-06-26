import disnake


def build_simple_embed(
    description: str, failure: bool = False, without_title: bool = False
) -> disnake.Embed:
    embed = disnake.Embed(
        title="Ошибка" if failure else "Успех",
        description=description,
        color=disnake.Color.dark_red() if failure else disnake.Color.dark_green(),
    ).set_footer(text="digital drugs technologies")
    if not without_title:
        embed.title = None
    return embed
