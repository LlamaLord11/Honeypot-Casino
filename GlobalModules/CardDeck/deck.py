import os, random

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

BASE_DIR = os.path.dirname(__file__)
DECK_PATH = os.path.join(BASE_DIR, "deck.txt")

def freshDeck():
    file = open(DECK_PATH, "r")
    lineCount = len(file.readlines())
    file.seek(0)
    deck = []

    for i in range(0,lineCount):
        currentLine = file.readline()
        currentLine = currentLine.split()

        suit = int(currentLine[0])
        if len(currentLine[1]) > 2:
            face = currentLine[1]
        else:
            face = int(currentLine[1])

        currentCard = Card(suit, face)
        deck.append(currentCard)
        

    file.close()
    return deck

def draw(deck):
    topCard = deck.pop(0)
    return topCard

def insert(deck, card):
    deck.append(card)

# End Deck Handling

# Deck Shuffling

def riffleShuffle(input):
    
    midpoint = int(len(input)/2 + random.randint(-1,1))
    shuffledDeck = []
    
    left = input[:midpoint]
    right = input[midpoint:]

    for i in range(0,len(input)):
        if len(left) == 0:
            shuffledDeck.extend(right)
            return shuffledDeck
        elif len(right) == 0:
            shuffledDeck.extend(left)
            return shuffledDeck
        else:
            oddEven = random.randint(1,2)

            match oddEven:
                case 1:
                    shuffledDeck.append(left[-1])
                    left.pop(-1)
                case 2:
                    shuffledDeck.append(right[-1])
                    right.pop(-1)

def shuffle(input):
    output = input
    for i in range(1,random.randint(4,12)):
        output = riffleShuffle(output)

    return output

# End Deck Shuffling