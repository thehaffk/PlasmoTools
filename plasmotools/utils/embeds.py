import disnake


def build_simple_embed(description: str, failure: bool) -> disnake.Embed:
    return disnake.Embed(
        title="Ошибка" if failure else "Успех",
        description=description,
        color=disnake.Color.dark_red() if failure else disnake.Color.dark_green(),
    ).set_footer(text="digital drugs technologies")
