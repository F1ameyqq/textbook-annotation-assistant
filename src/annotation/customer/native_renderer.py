"""Pure rendering components copied from frozen A26; no launcher/build call.
Original raw SHA256: 7b9860d9b0650166c93262f9f9c59b59b3bcb49b9e608df5dbc3e9603dd98f04
"""
import html
import re
from html.parser import HTMLParser

FORMULA = re.compile(r'\$\$[^$]+\$\$|\$[^$]+\$')

ZONES = {'question': 'question', 'choice': 'option', 'answer': 'answer', 'analysis': 'analysis'}

def need(value, message):
    if not value:
        raise ValueError(message)

def normalized(text):
    need(isinstance(text, str), 'TEXT_STRING_REQUIRED')
    return re.sub(r'<br\s*/?>', '\n', text.replace('\r\n', '\n'), flags=re.I)

def export_zone(record, zone):
    value = record.get(ZONES[zone])
    if value is None or value == '' or value == []:
        return ''
    if zone == 'choice':
        need(isinstance(value, list) and all(isinstance(x, str) for x in value), 'OPTION_ARRAY_OF_STRINGS_REQUIRED')
        return '\n'.join(normalized(x) for x in value)
    return normalized(value)

class Content(HTMLParser):
    """Preserve text/math and known image bytes; never execute source HTML."""
    def __init__(self, images, question, zone):
        super().__init__(convert_charrefs=True)
        self.images = images
        self.parts = []
        self.formulas = []
        self.used_images = []
        self.question, self.zone = question, zone

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'br':
            self.parts.append('<br>')
        elif tag == 'img':
            src = attrs.get('src')
            need(src in self.images, 'UNBOUND_NATIVE_IMAGE_REFERENCE')
            row = self.images[src]
            need(row['printed_question'] == self.question, 'CROSS_QUESTION_IMAGE_REFERENCE')
            self.used_images.append(src)
            self.parts.append('<figure><img src="data:%s;base64,%s" alt="%s" width="%d" height="%d"></figure>' % (
                row.get('mime','image/jpeg'), row['base64'], html.escape(attrs.get('alt', '题图'), quote=True), row['width'], row['height']))
        elif tag in ('p', 'div'):
            self.parts.append('<br>')
        else:
            raise ValueError('UNSUPPORTED_NATIVE_HTML_TAG_' + tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        need(tag in ('p', 'div', 'br', 'img'), 'UNSUPPORTED_NATIVE_END_TAG')
        if tag in ('p', 'div'):
            self.parts.append('<br>')

    def handle_data(self, text):
        position = 0
        for match in FORMULA.finditer(text):
            self.parts.append(html.escape(text[position:match.start()]).replace('\n', '<br>'))
            raw = match.group()
            tex = raw[2:-2] if raw.startswith('$$') else raw[1:-1]
            fid = 'q%d-%s-f%d' % (self.question, self.zone, len(self.formulas) + 1)
            self.formulas.append({'id': fid, 'printed_question': self.question, 'zone': self.zone,
                'tex': tex, 'raw_delimited_tex': raw})
            self.parts.append('<span class="formula" id="%s" data-tex="%s">\\(%s\\)</span>' %
                (fid, html.escape(tex, quote=True), html.escape(tex)))
            position = match.end()
        rest = text[position:]
        need('$' not in rest, 'UNMATCHED_MATH_DELIMITER')
        self.parts.append(html.escape(rest).replace('\n', '<br>'))

CSS = '''
*{box-sizing:border-box}html{background:#e8edf0;color:#1c2531;font-family:"Microsoft YaHei","SimSun",sans-serif}
body{margin:0}main{max-width:1080px;margin:36px auto;padding:0 24px}header{padding:20px 0 22px;border-bottom:2px solid #143a4a}
h1{font-size:28px;margin:0 0 12px;color:#143a4a}header p{margin:6px 0;line-height:1.65;font-size:14px;color:#556471}
article{background:white;padding:34px 42px;margin:24px 0;border-radius:8px;box-shadow:0 4px 18px #17313c0c}
.eyebrow{color:#517482;font-size:13px;letter-spacing:1px}h2{font-size:24px;margin:8px 0 24px;color:#143a4a}
.zone{font-size:19px;line-height:2.2;overflow-wrap:break-word;margin:14px 0}.zone h3{font-size:14px;color:#517482;letter-spacing:2px;margin:0 0 10px}
.answer{border-top:1px solid #dce6e9;padding-top:20px;margin-top:28px}.option{padding:12px 20px;background:#f5f8f9;border-radius:6px}
figure{margin:18px 0 22px;display:flex;justify-content:center}figure img{display:block;max-width:100%;height:auto;object-fit:contain}
.formula{display:inline-block;vertical-align:baseline;margin:0 2px}mjx-container{max-width:100%}footer{font-size:12px;line-height:1.8;color:#52616a;margin:28px 0}
@media print{html{background:white}main{max-width:none;margin:0;padding:0}article{box-shadow:none;break-after:page;margin:0;padding:15mm}header,footer{display:none}}
'''
