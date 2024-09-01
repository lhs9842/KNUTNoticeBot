import setting
import requests
import threading
import time
import sqlite3
from bs4 import BeautifulSoup
from urllib import parse

public_board = [["BBSMSTR_000000000059", "일반소식"], ["BBSMSTR_000000000060", "장학안내"], ["BBSMSTR_000000000055", "학사공지사항"]] # [boardId, 게시판 명칭]

db_conn = sqlite3.connect("NoticeBot.db", check_same_thread=False)
db_cur = db_conn.cursor()
db_cur.execute('SELECT * FROM sqlite_master WHERE type="table" AND name="final_ntt"') # 테이블 존재 여부 확인
r = db_cur.fetchall()
if r:
    print("기존 데이터를 불러옵니다.")
else:
    print("새로 데이터베이스를 구축합니다.")
    db_conn.execute('CREATE TABLE final_ntt(boardId TEXT, final_nttId TEXT)')
    for n in public_board:
        db_conn.execute('INSERT INTO final_ntt VALUES ("' + n[0] + '", "1049241")') # 초기값 부여 시 검색 대상 게시판 중 하나의 게시글 하나를 적당히 선택하여 그 게시글의 nttId로 지정할 것. 제대로 지정하지 않으면 최초 구동 시 Many Request로 텔레그램 API 서버가 오류 발생시킴.
        db_conn.commit()

def send_message(channel, message):
    encode_message = parse.quote(message)
    url = 'https://api.telegram.org/bot' + setting.bot_token + '/sendmessage?chat_id=' + channel + '&text=' + encode_message
    response = requests.get(url)
    url = 'https://api.line.me/v2/bot/message/broadcast'
    send_header = {
        "Content-Type" : "application/json",
        "Authorization" : "Bearer " + setting.line_token
        }
    send_data = {
        "messages" : [
            { "type" : "text", "text" : message }
            ]
        }
    
    response = requests.post(url, headers=send_header, json=send_data)
    if response.status_code != 200:
        print("ERROR!!" + str(response.status_code))

def find_new_ntt(board_info):
    try:
        url = 'https://www.ut.ac.kr/cop/bbs/' + board_info[0] + '/selectBoardList.do'
        response = requests.get(url, verify=False)
        if response.status_code == 200:
            db_cur.execute("SELECT final_nttId FROM final_ntt WHERE boardId='" + board_info[0] + "'")
            rows = db_cur.fetchall()
            final = int(rows[0][0])
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            result_id = soup.findAll('input', {'name':'nttId', 'type':'hidden'})
            r_n = soup.findAll('input', {'type':'submit'})
            result_name = []
            for n in r_n:
                na = n.get('value')
                if (na != "검색") & (na != "등록하기"): # 최상부 검색 버튼 및 최하부 페이지 만족도 조사 부분의 submit 버튼 예외 처리
                    result_name.append(na)
            count = 0
            result_name.reverse()
            result_id.reverse()
            for n in result_id:
                i = int(n.get('value'))
                if i == 0: # 최상부 검색 버튼 부분에 지정된 nttId 값 0에 대한 예외처리
                    break
                if i <= final:
                    count += 1
                    continue
                send_message(setting.all_notice_channel, "[" + board_info[1] + "] " + result_name[count] + " : http://www.ut.ac.kr/cop/bbs/" + board_info[0] + "/selectBoardArticle.do?nttId=" + str(i))
                db_conn.execute("UPDATE final_ntt SET final_nttId='" + str(i) + "' WHERE boardId='" + board_info[0] + "'")
                count += 1
                db_conn.commit()
    except:
        now = time.localtime()
        message = "EXCEPT!! " + board_info[1]
        message += "%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
        encode_message = parse.quote(message)
        url = 'https://api.telegram.org/bot' + setting.bot_token + '/sendmessage?chat_id=' + setting.admin_channel + '&text=' + encode_message
        response = requests.get(url)
        if response.status_code != 200:
            print("NETWORK ERROR!!" + str(response.status_code) + "\n" + message)
        find_new_ntt(board_info)

def Bot_Start():
    for c in public_board:
        find_new_ntt(c)
    threading.Timer(30, Bot_Start).start()

Bot_Start()
