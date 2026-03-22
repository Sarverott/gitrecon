import marimo

__generated_with = "0.21.1"
app = marimo.App()


@app.cell
def _():
    import bs4 # pip install beautifulsoup4
    import requests # pip install requests
    import marko # pip install marko
    import IPython # pip install IPython
    import urllib # standard lib of python3
    import json # standard lib of python3
    import yaml # pip install PyYAML
    import lark

    [requests, marko, IPython, urllib, bs4, yaml, json, lark]
    return IPython, bs4, marko, requests


@app.cell
def _():
    # as example the llm info briefing about task tool
    md_url = "https://taskfile.dev/llms.txt"
    md_url
    return (md_url,)


@app.cell
def _(md_url, requests):
    # rest get requesting
    md_text = requests.get(md_url).text
    md_text
    return (md_text,)


@app.cell
def _(marko, md_text):
    # making html based on md context
    html_from_md = marko.convert(md_text)
    html_from_md
    return (html_from_md,)


@app.cell
def _(IPython, html_from_md):
    # final display looks like this
    IPython.core.display.HTML(html_from_md)
    return


@app.cell
def _(bs4, html_from_md):
    raw_text = bs4.BeautifulSoup(html_from_md).text

    def _sentence_prep(wordline):
        wordline = wordline.lower()
        wordline = wordline.replace(',', ' COMMA ')
        wordline = wordline.replace(':', ' DASH ')  #wordline = wordline.strip()
        wordline = wordline.replace(';', ' SEPARATOR ')
        wordline = wordline.replace('#', ' HASHTAG ')
        wordline = wordline.replace('"', "''").replace('`', "'").replace("'", ' UPPERCOMMA ')
        wordline = wordline.replace('\t', ' TAB ')
        wordline = wordline.replace('\r', ' RETURN ')
        wordline = wordline.replace('[', '(').replace('{', '(').replace('(', ' BRACKETSTART ')
        wordline = wordline.replace(']', ')').replace('}', ')').replace(')', ' BRACKETSTOP ')
        wordline = wordline.replace('\\', '/').replace('/', ' SLASH ')
        wordline = wordline.replace('@', ' AT ')
        wordline = wordline.replace('&', ' AMPERSAND ')
        wordline = wordline.replace('|', ' PIPE ')
        wordline = wordline.replace('~', ' LAMBDA ')
        wordline = wordline.replace('*', ' ASTERISK ')
        wordline = wordline.replace('^', ' UPINDEX ')
        wordline = wordline.replace('%', ' PERCENT ')
        wordline = wordline.replace('$', ' DOLARSIGN ')
        wordline = wordline.replace('!', ' SHOUT ')
        wordline = wordline.replace('?', ' QUESTION ')
        wordline = wordline.replace('=', ' EQUALS ')
        wordline = wordline.replace('.', ' END ')
        wordline = wordline.replace('+', ' PLUS ')
        wordline = wordline.replace('_', ' FLOOR ')
        wordline = wordline.replace('>', ' GREATER ')
        wordline = wordline.replace('<', ' LESSER ')
        wordchain = [x.strip() for x in wordline.split(' ') if x.strip()]
        return wordchain
    [_sentence_prep(x.strip()) for x in raw_text.replace('.', '\n').split('\n') if x.strip()]
    return (raw_text,)


@app.cell
def _(raw_text):
    replace_matrix = {'0': 'ZERO', '1': 'JEDEN', '2': 'DWA', '3': 'TRZY', '4': 'CZTERY', '5': 'PIECI', '6': 'SZESCI', '7': 'SIEDEM', '8': 'OSIEM', '9': 'DZIEWIECI', ',': 'PRZECINEK', '-': 'DASZ', ':': 'DWUKROP', ';': 'SEPARATOR', '#': 'HASZTAG', '"': 'SKOKPRZECIN SKOKPRZECIN', '`': 'SKOKPRZECIN', "'": 'SKOKPRZECIN', '\t': 'TAB', '\r': 'WRACAJ', '[': 'STARTNAWIAS', '{': 'STARTNAWIAS', '(': 'STARTNAWIAS', ']': 'STOPNAWIAS', '}': 'STOPNAWIAS', ')': 'STOPNAWIAS', '\\': 'SLESZ', '/': 'SLESZ', '@': 'MAUPA', '&': 'AMPERSAND', '|': 'PIPE', '~': 'LAMBDA', '*': 'ASTERISK', '^': 'UPINDEX', '%': 'PERCENT', '$': 'DOLARSIGN', '!': 'SHOUT', '?': 'QUESTION', '=': 'EQUALS', '.': 'END', '+': 'PLUS', '_': 'FLOOR', '>': 'GREATER', '<': 'LESSER'}

    def _sentence_prep(wordline):
        global replace_matrix
        wordline = wordline.lower()
        for replacer in replace_matrix:
            wordline = wordline.replace(replacer, ' ' + replace_matrix[replacer] + ' ')
        wordchain = [x.strip() for x in wordline.split(' ') if x.strip()]
        return wordchain

    def text_to_tokenchain_sentences(textstr):
        textstr = textstr.replace('.', '\n')
        sentences = textstr.split('\n')
        return [_sentence_prep(sentence_str.strip()) for sentence_str in sentences if sentence_str.strip()]
    text_to_tokenchain_sentences(raw_text)  #'"': "''",  #.replace("`", "'").replace("'":"UPPERCOMMA",  # "[":"BRACKETSTART",  # "{":"BRACKETSTART",  # "(":"BRACKETSTART",  #"[", "(").replace("{", "(").replace("(":"BRACKETSTART",  #"]",",").replace("}",",").replace(")":"BRACKETSTOP",  #"\\", "/").replace("/":"SLASH",  # "]":"BRACKETSTOP",  # "}":"BRACKETSTOP",  # ")":"BRACKETSTOP",  #",").replace("}",",").replace(")":"BRACKETSTOP",  #"\\", "/").replace("/":"SLASH",  #wordline = wordline.strip()  # wordline = wordline.replace(",", " COMMA ")  # wordline = wordline.replace(":", " DASH ")  # wordline = wordline.replace(";", " SEPARATOR ")  # wordline = wordline.replace("#", " HASHTAG ")  # wordline = wordline.replace('"', "''").replace("`", "'").replace("'", " UPPERCOMMA ")  # wordline = wordline.replace("\t", " TAB ")  # wordline = wordline.replace("\r", " RETURN ")  # wordline = wordline.replace("[", "(").replace("{", "(").replace("(", " BRACKETSTART ")  # wordline = wordline.replace("]", ")").replace("}", ")").replace(")", " BRACKETSTOP ")  # wordline = wordline.replace("\\", "/").replace("/", " SLASH ")  # wordline = wordline.replace("@", " AT ")  # wordline = wordline.replace("&", " AMPERSAND ")  # wordline = wordline.replace("|", " PIPE ")  # wordline = wordline.replace("~", " LAMBDA ")  # wordline = wordline.replace("*", " ASTERISK ")  # wordline = wordline.replace("^", " UPINDEX ")  # wordline = wordline.replace("%", " PERCENT ")  # wordline = wordline.replace("$", " DOLARSIGN ")  # wordline = wordline.replace("!", " SHOUT ")  # wordline = wordline.replace("?", " QUESTION ")  # wordline = wordline.replace("=", " EQUALS ")  # wordline = wordline.replace(".", " END ")  # wordline = wordline.replace("+", " PLUS ")  # wordline = wordline.replace("_", " FLOOR ")  # wordline = wordline.replace(">", " GREATER ")  # wordline = wordline.replace("<", " LESSER ")
    return (text_to_tokenchain_sentences,)


@app.cell
def _(html_from_md, md_text, raw_text, text_to_tokenchain_sentences):
    import re
    import zlib

    glossary = dict()

    def paratangle(data):
        return [
            hex(zlib.adler32(data.encode("utf-8")))[2:],
            hex(zlib.crc32(data.encode("utf-8")))[2:]
        ]

    def check_a12y(testdata):
        acsii_letter_pattern = '[a-zA-Z]'
        check = re.compile(acsii_letter_pattern)
        return (check.match(testdata[0]) and check.match(testdata[-1]))

    def a12y(input_str):
        global glossary
        output_str = []
        if len(input_str) and check_a12y(input_str):
            output_str = [
                input_str[0],
                str(len(input_str)),
                input_str[-1]
            ]

        else:
            output_str = [
                "0",
                "-",
                hex(ord(input_str[0]))[2:],
                "-",
                hex(len(input_str))[2:],
                "-",
                hex(ord(input_str[-1]))[2:]
            ]
        keystr = "".join(output_str)
        if not keystr in glossary:
            glossary[keystr]=list()
    
        if not input_str in glossary[keystr]:
            glossary[keystr].append(input_str)
        if glossary[keystr].index(input_str) == 0:
            return f"{keystr}"
        else: 
            return f"{keystr}{glossary[keystr].index(input_str)}"

    ratfile = """
    @glossaries
    #strmode
    $WORDS
    !pipe_meanings
    """
    def spelling_rat(keystr, elements):
        d = [
            ".a12y_entry",
            f"${keystr}",
            "="+"\n+".join(elements),
            #f"%{len(elements)}",
            f":{"-".join(paratangle(keystr))}",
            "*"+"\n*".join(["-".join(paratangle(elem)) for elem in elements]),
            ""
        ]
        return "\n".join(d)

    tmp_text = [ "\n+".join([a12y(y) for y in x]) for x in text_to_tokenchain_sentences(raw_text)]

    for keyword in glossary:
        ratfile +=spelling_rat(keyword, glossary[keyword])

    ratfile += """
    @conversations
    #intmode
    $spellindex
    =0
    #strmode
    .build_sentence
    $sentence
    =WORDS.A12Y.
    """

    sentence_sep = """
    !talk_sentence
    #intmode
    $spellindex
    +1
    #strmode
    .build_sentence
    $sentence
    =WORDS.A12Y.\n
    """
    ratfile += sentence_sep.join(tmp_text)
    ratfile += """
    !talk_sentence
    <save
    """
    print("\t md_text:", len(md_text))
    print("\t html_text:", len(html_from_md))
    print("\t html_text:", len(raw_text))
    print("\t RAT Size:", len(ratfile))
    print("\t RAT Lines:", len(ratfile.split("\n")))
    print()
    print(ratfile)
    return (glossary,)


@app.cell
def _(glossary):
    glossary
    return


@app.cell
def _(requests):
    from lark import Lark
    json_parser = Lark(r"""
        value: dict
             | list
             | ESCAPED_STRING
             | SIGNED_NUMBER
             | "true" | "false" | "null"

        list : "[" [value ("," value)*] "]"

        dict : "{" [pair ("," pair)*] "}"
        pair : ESCAPED_STRING ":" value

        %import common.ESCAPED_STRING
        %import common.SIGNED_NUMBER
        %import common.WS
        %ignore WS

        """, start='value')

    x = requests.get("https://api.github.com/gists/public").text
    y = json_parser.parse(x)
    print( y.pretty() )
    return


@app.cell
def _(marko, requests):
    md = marko.Markdown()
    md.use('footnote')
    md.use('toc')
    md.use('codehilite')
    data = md(requests.get("https://github.com/Sarverott/Sarverott/raw/refs/heads/master/README.md").text)
    md.renderer.render_toc()
    return


@app.cell
def _():
    #IPython.core.display.HTML()
    return


if __name__ == "__main__":
    app.run()

