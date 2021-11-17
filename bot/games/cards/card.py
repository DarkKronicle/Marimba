import enum


class Suite(enum.Enum):
    diamonds = 0
    hearts = 1
    spades = 2
    clubs = 3

    @classmethod
    def __str__(cls):
        if cls == Suite.diamonds:
            return '♦'
        if cls == Suite.hearts:
            return '♥'
        if cls == Suite.spades:
            return '♠'
        if cls == Suite.clubs:
            return '♣'


class Card:

    __slots__ = ('suite', 'number')

    def __init__(self, suite, number):
        self.suite = suite
        self.number = number

    def __str__(self):
        return '{0}{1}'.format(str(self.suite), self.number)


class Deck:

    card_numbers = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
    card_suites = (Suite.diamonds, Suite.hearts, Suite.spades, Suite.clubs)

    def __init__(self):
        self.cards = []
        for suite in self.card_suites:
            for number in self.card_numbers:
                self.cards.append(Card(suite, number))
