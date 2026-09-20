import sys
from html.parser import HTMLParser

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'r', encoding='utf-8') as f:
    content = f.read()

class SafeFixParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.fixed_html = []
        self.void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        attr_str = ''.join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        self.fixed_html.append(f'<{tag}{attr_str}>')
        if tag not in self.void_elements:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return
        if not self.stack:
            return
        
        if self.stack[-1] == tag:
            self.stack.pop()
            self.fixed_html.append(f'</{tag}>')
        else:
            if tag in self.stack:
                if tag == 'div' and self.stack[-1] == 'main':
                    print('Refusing to pop main for an extra div')
                    return
                
                popped_tags = []
                while self.stack[-1] != tag:
                    popped = self.stack.pop()
                    popped_tags.append(popped)
                    if popped == 'main':
                        self.stack.append('main')
                        for t in reversed(popped_tags[:-1]):
                            self.stack.append(t)
                        print(f'Refused to pop main to match {tag}')
                        return
                    
                for popped in popped_tags:
                    self.fixed_html.append(f'</{popped}>')
                
                self.stack.pop()
                self.fixed_html.append(f'</{tag}>')
            else:
                return

    def handle_startendtag(self, tag, attrs):
        attr_str = ''.join([f' {k}="{v}"' if v is not None else f' {k}' for k, v in attrs])
        self.fixed_html.append(f'<{tag}{attr_str} />')

    def handle_data(self, data):
        self.fixed_html.append(data)

    def handle_entityref(self, name):
        self.fixed_html.append(f'&{name};')

    def handle_charref(self, name):
        self.fixed_html.append(f'&#{name};')

    def handle_comment(self, data):
        self.fixed_html.append(f'<!--{data}-->')

    def handle_decl(self, decl):
        self.fixed_html.append(f'<!{decl}>')

parser = SafeFixParser()
parser.feed(content)

while parser.stack:
    popped = parser.stack.pop()
    parser.fixed_html.append(f'</{popped}>')

with open('frontend/src/app/pages/inadimplencia/inadimplencia.component.html', 'w', encoding='utf-8') as f:
    f.write(''.join(parser.fixed_html))
