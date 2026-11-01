"""Source-bound image references and escaped inline TeX for native fields."""
import re
from html import escape
from .store import Hold

FORMULA=re.compile(r'\$\$[^$]+\$\$|\$[^$]+\$')


def zone_html(text,images=()):
    remainder=FORMULA.sub('',text)
    if '$' in remainder or '\\' in remainder:raise Hold('公式请用成对的 $ 包围；保留正常文字在公式外。')
    for match in FORMULA.finditer(text):
        if re.search(r'\\(?:href|url|html\w*|class|style|cssId|require|includegraphics|input|newcommand|def)\b',match.group()):
            raise Hold('公式包含当前本地排版不支持的扩展或外部引用。')
        depth=0
        for token in re.findall(r'\\.|[{}]',match.group()):
            if token=='{':depth+=1
            elif token=='}':depth-=1
            if depth<0:raise Hold('公式括号不配对。')
        if depth:raise Hold('公式括号不配对。')
    value=escape(text,quote=True).replace('\n','<br>')
    for frame in images:
        value+='<br><img src="'+escape(frame['image_path'],quote=True)+'" alt="来源题图">'
    return value
