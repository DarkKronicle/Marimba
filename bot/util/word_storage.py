import pathlib
from collections import defaultdict, Counter
import random


alphabet = list('abcdefghijklmnopqrstuvwxyz')


class Word:

    __slots__ = ('word', 'length', 'sorted')

    def __init__(self, word):
        self.word = word.lower()
        self.length = len(self.word)
        self.sorted = Counter(self.word)

    def __contains__(self, item):
        item_length = len(item)
        if self.length < item_length:
            # A bigger word can't be found in a smaller one
            return False
        if isinstance(item, Word):
            item = item.sorted
        elif isinstance(item, AnagramSet):
            item = item.words[0].sorted
        elif not isinstance(item, list):
            item = Counter(list(item))
        if self.sorted == item:
            return True
        return all(self.sorted[x] >= item[x] for x in item)

    def remove(self, items):
        word = list(self.word)
        try:
            for i in items:
                word.remove(i)
        except Exception as e:
            print('{0} - {1}'.format(word, items))
            raise e
        self.word = ''.join(word)
        self.length = len(self.word)
        self.sorted = Counter(self.word)

    def copy(self):
        return Word(self.word)

    def __getitem__(self, item):
        return self.word[item]

    def __len__(self):
        return self.length


class AnagramSet:

    __slots__ = ('sorted', 'words', 'length', 'word')

    def __init__(self, *words):
        self.words = [Word(w) for w in words]
        self.length = len(self.words[0])

    def append(self, item):
        self.words.append(Word(item))

    def __len__(self):
        return self.length

    def size(self):
        return len(self.words)

    def __contains__(self, item):
        return item in self.word[0]


class WordStorage:

    def __init__(
            self,
            fp='./storage/words/',
            *,
            all_words='words.txt',
            common_words='google-10000-english-no-swears.txt',
            long_words='google-10000-english-usa-no-swears-long.txt'
    ):
        # Use str(fp) just in case it's already a path object
        word_path = pathlib.Path(str(fp) + '/' + str(all_words))
        common_path = pathlib.Path(str(fp) + '/' + str(common_words))
        long_path = pathlib.Path(str(fp) + '/' + str(long_words))

        self.words = defaultdict(dict)
        for line in word_path.read_text().splitlines():
            line_length = len(line)
            if line_length < 1:
                continue
            if line[0] == '#':
                # Comments (mainly license and credits)
                continue
            line_sort = ''.join(sorted(line))
            word_set = self.words[line_length].get(line_sort)
            if word_set:
                word_set.append(line)
                continue
            self.words[len(line)][line_sort] = AnagramSet(line)
        print(sum([len(word.values()) for word in self.words.values()]))

        self.common_words = []
        for line in common_path.read_text().splitlines():
            if len(line) < 1:
                continue
            if line[0] == '#':
                continue
            word = Word(line)
            self.common_words.append(word)

        self.long_words = []
        for line in long_path.read_text().splitlines():
            if len(line) < 1:
                continue
            if line[0] == '#':
                continue
            word = Word(line)
            self.long_words.append(word)

    def _find_anagram(self, min_length, base, *, multi_word=False, cache=None, exact=False):
        found = []
        if cache is None:
            # Build cache for multi word anagrams
            # We know that further anagrams only exist within anagrams of the main word
            for i in range(min_length, base.length + 1):
                for word_set in self.words[i].values():
                    if word_set in base:
                        if not exact or len(word_set) == len(base):
                            # Return words if applicable
                            for word in word_set.words:
                                yield word.word
                        found.append(word_set)
        else:
            # Check cache for previous matches and see if they are applicable
            for word_set in cache:
                if word_set in base:
                    for word in word_set.words:
                        if not exact or len(word_set) == len(base):
                            yield word.word
                    found.append(word_set)
        if not multi_word:
            # Stop searching
            return
        for word in found:
            # Create copy with found anagram removed.
            base_copy = base.copy()
            base_copy.remove(word.words[0])
            if len(base_copy) < min_length:
                extra_found = []
            else:
                # Recursion
                extra_found = self._find_anagram(min_length, base_copy, cache=found, multi_word=multi_word, exact=exact)
            for w in word.words:
                # Return built phrases
                for e in extra_found:
                    yield w.word + ' ' + e
        return

    def anagram(self, word, *, min_length=1, multi_word=False, max_num=5000, exact=False):
        # First construct into a word for usability
        word = Word(word)
        words = []
        for i, w in enumerate(self._find_anagram(min_length, word, multi_word=multi_word, exact=exact)):
            if i >= max_num:
                return words
            words.append(w)
        return words

    def get_anagram_word(self, length):
        return random.choice(self.long_words).word[:length]
