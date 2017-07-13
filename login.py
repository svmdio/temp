#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 12 14:15:09 2017

@author: timofey
"""

import cgi
import html
import sqlite3


form = cgi.FieldStorage()
login = form.getfirst('Login')
password = form.getfirst('Password')
login = html.escape(login)
password = html.escape(password)

#login = 'test@smtp.com'
#password = 'qwerty'
with sqlite3.connect('users.db') as conn:
    c = conn.cursor()
    t = (login,password)
    c.execute('SELECT * FROM users WHERE login = ? AND password = ?',t)
    data = c.fetchone()
    if not data:
        print("Content-type: text/html\n")
        print("""<!DOCTYPE HTML>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Обработка данных форм</title>
        </head>
        <body>""")
        print('access denied')
        print('</body>,</html>')
    else:
        print("Content-type: text/html\n")
        print("""<!DOCTYPE HTML>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Обработка данных форм</title>
        </head>
        <body>""")

        print("<h1>Обработка данных форм!</h1>")
        print("<p>LOGIN: {}</p>".format(login))
        print("<p>PASSWORD: {}</p>".format(password))

        print("""</body>
        </html>""")

print('done')
