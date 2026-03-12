import os, random

# Constants

SHUFFLE_OFFSET = 0.05 # Percentage of deck length to offset shuffle midpoint.
BURST_SIZE = 3 # Max number of cards to shuffle at once during riffle shuffle. It will be 1 to BURST_SIZE cards.

class Card:
# 1 = hearts, 2 = diamonds, 3 = spades, 4 = clubs
    def __init__(self, suitValue, faceValue):
        self.faceValue = faceValue
        self.suit = self.setSuit(suitValue)
        self.suitValue = suitValue 
        self.isAce = False

        if isinstance(faceValue, str):
            self.face = faceValue
            self.value = 10
        elif faceValue == 1:
            self.face = "Ace"
            self.value = 1
            self.isAce = True
        else:
            self.face = faceValue
            self.value = faceValue

    def __str__(self):
        return f"{self.face} of {self.suit}"   
    
    def setSuit(self, suitValue):
        match suitValue:
            case 1:
                return "Hearts"
            case 2:
                return "Diamonds"
            case 3:
                return "Spades"
            case 4:
                return "Clubs"
            case _:
                return "Error"

# End of Card Class

# Deck Handling

class Deck:
    def __init__(self, deckCount = 1):

        self.BASE_DIR = os.path.dirname(__file__)
        self.DECK_PATH = os.path.join(self.BASE_DIR, "deck.txt")
        self.deckCount = deckCount
        self.deck = self.freshDeck()

    def freshDeck(self):
        file = open(self.DECK_PATH, "r")
        lineCount = len(file.readlines())
        file.seek(0)
        singleDeck = []

        for i in range(0,lineCount):
            currentLine = file.readline()
            currentLine = currentLine.split()

            suit = int(currentLine[0])
            if len(currentLine[1]) > 2:
                face = currentLine[1]
            else:
                face = int(currentLine[1])

            currentCard = Card(suit, face)
            singleDeck.append(currentCard)
            

        file.close()
        return singleDeck * self.deckCount

    def draw(self):
        topCard = self.deck.pop(0)
        return topCard

    def insert(self, card):
        self.deck.append(card)

# End Deck Handling

# Deck Shuffling

    def riffleShuffle(self):
        offset = int(len(self.deck) * SHUFFLE_OFFSET)
        midpoint = int(len(self.deck)/2 + random.randint(-offset, offset))
        shuffledDeck = []
        left = self.deck[:midpoint]
        right = self.deck[midpoint:]

        while left or right:
            if not left:
                shuffledDeck.extend(right)
                break
            elif not right:
                shuffledDeck.extend(left)
                break
            else:
                burst = random.randint(1, BURST_SIZE)
                if random.randint(1, 2) == 1:
                    shuffledDeck.extend(left[:burst])
                    left = left[burst:]
                else:
                    shuffledDeck.extend(right[:burst])
                    right = right[burst:]

        self.deck = shuffledDeck

    def shuffle(self):
        for i in range(random.randint(4,12)):
            self.riffleShuffle()

# End Deck Shuffling

# Card Path Collector

BASE_DIR = os.path.dirname(__file__)
IMAGE_DIR = os.path.join(BASE_DIR, "CardImages")

def getCardPath(cardName: str):
    file = f"{cardName}.png"
    imagePath = os.path.join(IMAGE_DIR, file)
    if os.path.exists(imagePath):
        return True, imagePath
    else:
        return False, f"No card with name {cardName}"
