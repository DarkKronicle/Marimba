from pathlib import Path
import random


class OnTheSpotDeck:

    def __init__(self, name, entries):
        self.name = name
        self.entries: list = entries
        self.deck = entries.copy()

    @classmethod
    def from_file(cls, fp):
        fp = Path(str(fp))
        name = fp.stem.lower()
        with open(str(fp), 'r') as file:
            entries = file.readlines()
        return cls(name, entries)

    def copy(self):
        return OnTheSpotDeck(self.name, [entry for entry in self.entries]).shuffle()

    def shuffle(self):
        random.shuffle(self.deck)
        return self

    def reset_deck(self):
        self.deck = self.entries.copy()
        self.shuffle()

    def draw(self, n=1):
        selection = []
        for i in range(n):
            if not self.deck:
                self.reset_deck()
            selection.append(self.deck.pop(0))
        return selection


class OnTheSpotDeckHolder:

    def __init__(self):
        self.decks = {}
        deck_dir = Path('./storage/onthespot/')
        for file in deck_dir.glob('**/*.txt'):
            deck = OnTheSpotDeck.from_file(file)
            self.decks[deck.name] = deck

    def __getitem__(self, item):
        return self.decks[item].copy()
