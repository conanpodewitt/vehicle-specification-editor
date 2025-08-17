from pygments.style import Style
from pygments.token import Token, Comment, Keyword, Name, String, \
     Error, Generic, Number, Operator

class VSE(Style):

    styles = {
        Token:                  '',
        Comment:                '#3a7f1a', #Green
        Keyword:                '#2257e7', #Blue
        Name:                   '#12ba87', #light greeen
        String:                 '#df6400',
        Number:                 '#b2f883', #pale green
        Operator:               '#ffffff' #White
    }
