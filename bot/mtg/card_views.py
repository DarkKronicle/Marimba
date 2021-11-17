import discord
from scrython.cards.cards_object import CardsObject


def append_exists(message, **kwargs):
    for k, v in kwargs.items():
        if isinstance(v, tuple):
            m = v[0]
            suffix = v[1]
        else:
            m = v
            suffix = ''
        if m is None:
            continue
        message = message + f'**{k}:** {m}{suffix}\n'
    return message


def try_or_false(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except:
        return False


def get_stat_string(card: CardsObject):
    message = ''
    rarity = card.rarity()
    if rarity == 'uncommon':
        message += '🇺'
    elif rarity == 'common':
        message += '🇨'
    elif rarity == 'rare':
        message += '🇷'
    elif rarity == 'mythic':
        message += '🇲'
    if try_or_false(card.foil):
        message += '✨'
    if try_or_false(card.promo):
        message += '💵'
    if try_or_false(card.story_spotlight):
        message += '📘'
    if try_or_false(card.reserved):
        message += '⛔'

    return message


def color_from_card(card):
    try:
        if card.colors() is None:
            return discord.Colour.light_gray()
        try:
            color = card.colors()[0]
        except IndexError:
            color = card.colors()
    except KeyError:
        return discord.Colour.light_grey()
    if color == 'W':
        return discord.Colour.lighter_gray()
    if color == 'U':
        return discord.Colour.blue()
    if color == 'R':
        return discord.Colour.red()
    if color == 'B':
        return discord.Colour.darker_grey()
    if color == 'G':
        return discord.Colour.green()
    return discord.Colour.dark_grey()


def card_image_embed(card: CardsObject):
    description = append_exists('', Set=card.set_name(), CMC=card.cmc(), Price=(card.prices('usd'), '$'))
    description = description + '\n' + get_stat_string(card)
    embed = discord.Embed(
        description=description,
        colour=color_from_card(card)
    )
    embed.set_author(name=card.name() + ' - Image', url=card.scryfall_uri())
    layout = card.scryfallJson['layout']
    double = layout == 'transform' or layout == 'double_faced_token'
    try:
        faces = card.card_faces()
        embed.set_image(url=faces[0]['image_uris']['large'])
        embed.set_thumbnail(url=faces[1]['image_uris']['large'])
        if card.released_at() is not None:
            embed.set_footer(text=card.released_at())
        return embed
    except KeyError:
        pass
    try:
        url = card.image_uris(0, 'large')
    except:
        url = None
    if url is not None:
        embed.set_image(url=str(url))
    if double:
        embed.set_thumbnail(url=str(card.image_uris(1, 'large')))
    if card.released_at() is not None:
        embed.set_footer(text=card.released_at())
    return embed
