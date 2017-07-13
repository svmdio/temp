# -*- coding: utf8 -*-
#!/usr/bin/env python

import cgi
import html
import datetime
import requests
import gspread
import sys
from oauth2client.service_account import ServiceAccountCredentials
from decimal import Decimal



# константы используемые скриптом
GET_TOKEN_URL = "https://****/token.json" #запрос токена
# запросы данных
GET_DATA_URL1 = "https://****/campaigns.json"
GET_DATA_URL2 = "https://****/campaigns/{}/statistics.json"
#файл для аутенификации в гугл докс
CRED_FILE="API Project-394ed270d4.json"
#email для выдачи права доступа к создаваемой таблице
#WRITER_EMAIL='s@gmail.com'
#имя рабочей таблицы
#SPREADSHEET_NAME="spreadsheet_name"

#ф-ия создания шапки таблицы
#на вход принимает лист таблицы, номер запуска внутри дня, номер листа (дневные данные,месячные)
def print_header(_sheet, _attempt_num, _sheet_num):
  #здесь и далее _sheet.update_cell - заполнение ячеек листа первый параметр 1 - номер строки, второй параметр 1 - номер столбца
  _sheet.update_cell(1, 1, "CampaingId" if _sheet_num==1 else "")
  _sheet.update_cell(1, 2, "Date" if _sheet_num==1 else "Month")
  _sheet.update_cell(1, 3, "url_object_id")
  _sheet.update_cell(1, 4, "achievement_count")
  _sheet.update_cell(1, 6, "Amount 1" if _sheet_num==1 else "Amount")
  _sheet.update_cell(1, 7, "Amount 2" if _sheet_num==1 else "Clicks")
  _sheet.update_cell(1, 8, "Clicks 1" if _sheet_num==1 else "Shows")
  if _sheet_num==1: _sheet.update_cell(1, 9, "Clicks 2")
  if _sheet_num==1: _sheet.update_cell(1,10, "Shows 1")
  if _sheet_num==1: _sheet.update_cell(1,11, "Shows 2")
  if _sheet_num==1: _sheet.update_cell(1,12, _attempt_num) #здесь будем хранить какой по счету был запуск скрипта в течении дня

#ф-ия заполнения таблицы данными
#на вход принимает лист таблицы, данные, номер запуска внутри дня, номер листа (дневные данные,месячные)
def print_attempt(_sheet, _camp_data, _attempt_num, _sheet_num):
  _str_num = 2
  _month_data=dict() #здесь будем агрегировать данные помесячно
  for arr1 in _camp_data["daily_data"]:
     if _sheet_num==1:
        _sheet.update_cell(_str_num, 1, arr1["id"])
        _sheet.update_cell(_str_num, 2, arr1["date"])
        _sheet.update_cell(_str_num, 3, arr1["url_object_id"])
        _sheet.update_cell(_str_num, 4, arr1["achievement_count"])
        _sheet.update_cell(_str_num, 5, arr1["cr"])
        _sheet.update_cell(_str_num, 6 if _attempt_num == 1 else 7, arr1["amount"])
        _sheet.update_cell(_str_num, 8 if _attempt_num == 1 else 9, arr1["clicks"])
        _sheet.update_cell(_str_num, 10 if _attempt_num == 1 else 11, arr1["shows"])
        _str_num += 1
     else:
        _month_num = arr1["date"].month
        _url_object_id = arr1["url_object_id"]

        if _month_data.get(_month_num) is None:
           _month_data.update({_month_num:{_url_object_id:{"amount":0,"clicks":0,"shows":0,"cr":0,"achievement_count":0}}})
        if _month_data.get(_month_num).get(_url_object_id) is None:
           _month_data.update({_month_num:{_url_object_id:{"amount":0,"clicks":0,"shows":0,"cr":0,"achievement_count":0}}})

        _month_data[_month_num][_url_object_id]["amount"] += arr1["amount"]
        _month_data[_month_num][_url_object_id]["shows"] += arr1["shows"]
        _month_data[_month_num][_url_object_id]["cr"] += arr1["cr"]
        _month_data[_month_num][_url_object_id]["achievement_count"] += arr1["achievement_count"]
  if _sheet_num==2:
     for month in _month_data:
        for url in _month_data[month]:
           _sheet.update_cell(_str_num, 2, month)
           _sheet.update_cell(_str_num, 3, url)
           _sheet.update_cell(_str_num, 4, _month_data[month][url]["achievement_count"])
           _sheet.update_cell(_str_num, 6, _month_data[month][url]["amount"])
           _sheet.update_cell(_str_num, 7, _month_data[month][url]["clicks"])
           _sheet.update_cell(_str_num, 8, _month_data[month][url]["shows"])       
           _str_num += 1

#функция возвращает список campaings
def get_campaings(_json):
  _prev_campaing = ""
  _ret=list()
  for arr1 in _json:
     if _prev_campaing != arr1["id"]:
        _ret.append(arr1["id"])
        _prev_campaing=arr1["id"]
  return _ret

#
def get_campaings_stats(_json):
  _stats=list()
  _ret=dict()   
  for arr1 in _json:
     for arr2 in arr1["stats_full"]:
        _stats.append({"id":arr1["id"],
           "date": datetime.datetime.strptime(arr2["date"],'%d.%m.%Y'),
           "amount": Decimal(arr2["amount"]),
           "shows": Decimal(arr2["shows"]),
           "url_object_id": arr1["banners"][0]["url_object_id"],
                               "cr":0,
                               "achievement_count":0})
  _ret.update({"daily_data":_stats})
  return dict(_ret)

#
def get_campaings_data(_stats, _id, _camp_json):
  _ret = _stats
  for arr1 in _camp_json["banners"]:
     for arr2 in _ret["daily_data"]:
        if (arr2["id"]==_id) and (arr2["date"]==datetime.datetime.strptime(arr1["date"],'%Y-%m-%d')):
           if not arr1.get("conversions") is None:
              arr2["achievement_count"]+=Decimal(arr1["conversions"][0]["achievement_count"])

  return _ret


#тут точка входа в программу
if __name__ == '__main__':
  #обработка формы
  form = cgi.FieldStorage()
  refresh_token = form.getfirst('Refresh_Token','не задано')
  client_id = form.getfirst('Client_ID','не задано')
  refresh_token = html.escape(refresh_token)
  client_id = html.escape(client_id)
  client_secret = form.getfirst('Client_Secret','не задано')
  client_secret = html.escape(client_secret)
  writer_email = form.getfirst('Writer_Email','не задано')
  WRITER_EMAIL = html.escape(writer_email)
  spreadsheet_name = form.getfirst('Spreadsheet_Name','не задано')
  SPREADSHEET_NAME = html.escape(spreadsheet_name)

  #формуруем параметры запроса на токен
  formdata = {
     "grant_type":"refresh_token",
     "refresh_token":refresh_token,
     "client_id":client_id,
     "client_secret":client_secret,
  }

  #делаем запрос к вебсерверу
  try:
     r = requests.post(GET_TOKEN_URL, formdata)
  except requests.exceptions.RequestException as e:
     #в случае возникновения исключения выодим на экран ошибку и выходим
     print(e)
     sys.exit(1)

  #выходим, если сервер не вернул статус 200
  if r.status_code != 200:
     print(r.text)
     print("Token request is invalid or malformed")
     sys.exit(1)

  #получаем токен
  access_token = r.json()["access_token"];

  #1-й запрос на данные
  try:
     r = requests.get(GET_DATA_URL1, headers={"Authorization":"Bearer {}".format(access_token)})
  except requests.exceptions.RequestException as e:
     print(e)
     sys.exit(1)

  #выходим, если сервер не вернул статус 200
  if r.status_code != 200:
     print("Data request \"{}\" is invalid".format(GET_DATA_URL1))
     sys.exit(1)

  first_json = r.json()

  #получаем дневные данные по кампаниям
  camp_data = get_campaings_stats(first_json)

  #получаем список кампаний
  campaings=get_campaings(first_json)

  #пробегаемся по сформированному на прошлом шаге списку и отправляем запрос #2 на данные
  for campaing in campaings:
     try:
        r = requests.get(GET_DATA_URL2.format(campaing), headers={"Authorization":"Bearer {}".format(access_token)})
     except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)

     if r.status_code != 200:
        print("Data request \"{}\" is invalid".format(GET_DATA_URL2))
        sys.exit(1)
     #дополняем ежедневные данные по кампаниям данными из второго запроса
     camp_data = get_campaings_data(camp_data, campaing, r.json())

  #задаем параметры для коиента гугл докс
  scope=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
  creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)

  try:
     #создаем клиента гугл докс
     client = gspread.authorize(creds)
  except:
     print(sys.exc_info()[0])
     sys.exit(1)

  try:
     #пытаемся открыть таблицу
     spreadsheet = client.open(SPREADSHEET_NAME)
  except gspread.SpreadsheetNotFound:
          #таблица не найдена значит будем ее создавать
     print("Spreadsheet not found. Create...")
     spreadsheet = client.create(SPREADSHEET_NAME)
          #дадим права пользователю, который будет просматривать и возможно редактировать эту таблицу
     spreadsheet.share(WRITER_EMAIL, role='writer')
     sheet = spreadsheet.sheet1

  #всегда, когда создается новая таблица она имеет всего один лист
  sheet2 = spreadsheet.get_worksheet(1)
  #если второго листа нет, то создадим его
  if sheet2 is None:
     sheet2 = spreadsheet.add_worksheet("month",512,10)
  sheet2.clear()

  if sheet.cell(1,12).value=='2':
     print("Clear sheet...")
     attempt_num = 1
     sheet.clear()
  else:
     attempt_num = 2

  #заполняем листы данными (см. описание ф-ий)
  print_header(sheet, attempt_num, 1)
  print_attempt(sheet, camp_data, attempt_num, 1)
  print_header(sheet2, attempt_num, 2)