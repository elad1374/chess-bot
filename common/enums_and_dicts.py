from enum import IntEnum

class PieceType(IntEnum):
    BISHOP = 0
    KING = 1
    KNIGHT = 2
    PAWN = 3
    QUEEN = 4
    ROOK = 5

    @property
    def label(self):
        return self.name.lower()

class ColoredPieceType(IntEnum):
    BLACK_BISHOP = 0
    BLACK_KING = 1
    BLACK_KNIGHT = 2
    BLACK_PAWN = 3
    BLACK_QUEEN = 4
    BLACK_ROOK = 5
    WHITE_BISHOP = 6
    WHITE_KING = 7
    WHITE_KNIGHT = 8
    WHITE_PAWN = 9
    WHITE_QUEEN = 10
    WHITE_ROOK = 11

    @property
    def label(self):
        return self.name.lower()

    @property
    def piece_type(self):
        """Return the underlying non-colored PieceType for this piece."""
        return PieceType(self.value % 6)

    @classmethod
    def parse(cls, notation: str):
        """Parse FEN notation, color+piece abbreviations, or a class index string."""

        token = str(notation).strip()
        if not token:
            raise ValueError("invalid chess notation")

        if token.isdigit():
            value = int(token)
            if value not in cls._value2member_map_:
                raise ValueError("invalid chess notation")
            return cls(value)

        if token in FEN_TO_INT:
            return cls(FEN_TO_INT(token))

        normalized = token.lower().replace(" ", "-")

        if normalized in CLASS_TO_INT:
            return cls(CLASS_TO_INT[normalized])

        if len(normalized) == 2 and normalized[0] in {"b", "w"} and normalized[1] in {"b", "k", "n", "p", "q", "r"}:
            color_offset = 0 if normalized[0] == "b" else 6
            piece_offset = {"b": 0, "k": 1, "n": 2, "p": 3, "q": 4, "r": 5}[normalized[1]]
            return cls(color_offset + piece_offset)

        raise ValueError("invalid chess notation")

FEN_TO_INT = {
    'b': 0,   # black-bishop
    'k': 1,   # black-king
    'n': 2,   # black-knight
    'p': 3,   # black-pawn
    'q': 4,   # black-queen
    'r': 5,   # black-rook
    'B': 6,   # white-bishop
    'K': 7,   # white-king
    'N': 8,   # white-knight
    'P': 9,   # white-pawn
    'Q': 10,  # white-queen
    'R': 11   # white-rook
}
INT_TO_FEN = {
    0: 'b',  # black-bishop
    1: 'k',  # black-king
    2: 'n',  # black-knight
    3: 'p',  # black-pawn
    4: 'q',  # black-queen
    5: 'r',  # black-rook
    6: 'B',  # white-bishop
    7: 'K',  # white-king
    8: 'N',  # white-knight
    9: 'P',  # white-pawn
    10: 'Q', # white-queen
    11: 'R'  # white-rook
}

INT_TO_NAME = ["black-bishop", "black-king", "black-knight", "black-pawn", "black-queen", "black-rook", 
               "white-bishop", "white-king", "white-knight", "white-pawn", "white-queen", "white-rook"]

CLASS_TO_INT = {"black-bishop":0, "black-king":1, "black-knight":2, "black-pawn":3, "black-queen":4, "black-rook":5, 
               "white-bishop":6, "white-king":7, "white-knight":8, "white-pawn":9, "white-queen":10, "white-rook":11}

PROMOTED_PIECES = {
    'b' : PieceType.BISHOP,
    'n' : PieceType.KNIGHT,
    'q' : PieceType.QUEEN,
    'r' : PieceType.ROOK
}

COLOR_TO_INT = {
    "black": 0,
    "white": 1
}
MAX_LIMITS = {
    'king': 1,
    'queen': 1, 
    'knight': 2,
    'rook': 2,
    'bishop': 2,
    'pawn': 8
}

class Orientation(IntEnum):
    """Enum representing the orientation state of a piece using integers."""
    LYING = 0
    STANDING = 1