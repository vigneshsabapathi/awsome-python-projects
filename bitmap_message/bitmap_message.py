"""Bitmap Message — display a user message according to a 2-tone bitmap.

Inspired by Al Sweigart's "Bitmap Message" project. The bitmap is a multi-line
string where space characters represent empty space and any other character is
replaced with characters from the user's message (cycled with a modulo).

The bitmap below is a simple original diamond pattern. To use Al Sweigart's
world-map bitmap from his book, replace BITMAP with the contents of
https://inventwithpython.com/bitmapworld.txt — the program is bitmap-agnostic.

Tags: tiny, beginner, artistic
"""
import sys

# The first and last lines of 68 dots are a visual ruler — they're treated as
# non-space characters too, so they print as a frame using the user's message.
DIAMOND = """
....................................................................

                                  *
                                 ***
                                *****
                               *******
                              *********
                             ***********
                            *************
                           ***************
                          *****************
                         *******************
                        *********************
                         *******************
                          *****************
                           ***************
                            *************
                             ***********
                              *********
                               *******
                                *****
                                 ***
                                  *

...................................................................."""

TRIANGLE = """
....................................................................

                                  *
                                 ***
                                *****
                               *******
                              *********
                             ***********
                            *************
                           ***************
                          *****************
                         *******************
                        *********************
                       ***********************
                      *************************
                     ***************************
                    *****************************
                   *******************************
                  *********************************
                 ***********************************
                *************************************
               ***************************************

...................................................................."""

HEART = """
....................................................................

           *********               *********
         *************           *************
       *****************       *****************
      *******************************************
     *********************************************
     *********************************************
      *******************************************
       *****************************************
        ***************************************
         *************************************
          ***********************************
            *******************************
              ***************************
                ***********************
                  *******************
                    ***************
                      ***********
                        *******
                          ***
                           *

...................................................................."""

CIRCLE = """
....................................................................

                       ********************
                  ******************************
                **********************************
              **************************************
             ****************************************
            ******************************************
           ********************************************
          **********************************************
          **********************************************
          **********************************************
          **********************************************
          **********************************************
           ********************************************
            ******************************************
             ****************************************
              **************************************
                **********************************
                  ******************************
                       ********************

...................................................................."""

# Mapping of preset names to bitmap strings. UIs use this for the picker.
PRESETS = {
    'Diamond': DIAMOND,
    'Triangle': TRIANGLE,
    'Heart': HEART,
    'Circle': CIRCLE,
}

# Backwards-compat alias used by the original CLI.
BITMAP = DIAMOND


def render(bitmap: str, message: str) -> str:
    """Render `bitmap` filled with characters cycled from `message`.
    Spaces in the bitmap stay as spaces; any other character is replaced by
    `message[i % len(message)]` where i is the column index within the line."""
    if not message:
        raise ValueError('message must be non-empty')
    out_lines = []
    for line in bitmap.splitlines():
        chars = []
        for i, bit in enumerate(line):
            chars.append(' ' if bit == ' ' else message[i % len(message)])
        out_lines.append(''.join(chars))
    return '\n'.join(out_lines)


def main() -> None:
    print('Bitmap Message')
    print('Enter the message to display with the bitmap.')
    message = input('> ')
    if message == '':
        sys.exit()
    print(render(BITMAP, message))


if __name__ == '__main__':
    main()
