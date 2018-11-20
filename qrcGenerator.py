#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
files = os.listdir('icons/')
iconsList = []
for f in files:
  name = f.split('.')
  if len(name) > 1:
    if name[1] == 'png' or name[1] == 'ico':
      iconsList.append(u'<file>icons/{}.{}</file>\n'.format(name[0], name[1]))
text = '<RCC>\n<qresource prefix="icons">\n'
for row in iconsList:
  text += row
text += '</qresource>\n</RCC>'
print text
file = open('icons.qrc','w')
file.write(text)
file.close()

