import jwt #Pyjwt
import datetime
import hashlib
import requests
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from pymongo import MongoClient
from bs4 import BeautifulSoup

app = Flask(__name__)

client = MongoClient('mongodb://localhost', 27017)
db = client.deunggae

# 토큰 비밀 키
SECRET_KEY = 'SPARTA'

@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "name":"",                                                  # 이름
        "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png", # 프로필 사진 기본 이미지
        "profile_info": ""                                          # 프로필 한 마디
    }
    db.users.insert_one(doc)
    # print(f'id: {username_receive}, pw : {password_receive}')
    return jsonify({'result': 'success'})

# 아이디 중복 확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    # ID 중복확인
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    if exists == False:
        return jsonify({'result': 'success'})
    elif exists == True:
        return jsonify({'result': 'fail'})

# 회원탈퇴
@app.route('/sign_delete', methods=['POST'])
def sign_delete():
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    password_receive = request.form['password_give']
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = list(db.users.find({'password': pw_hash}))

    for name in result:
        if payload['id'] == name['username']:
            if name is not None:
                db.users.delete_one({'username':payload['id']})
                return jsonify({'msg': '삭제 되었습니다.','result': 'success'})
            #실패시
            else:
                return jsonify({'result': 'fail', 'msg': '비밀번호가 일치하지 않습니다.'})


# 포스팅 전체 글 불러오기
@app.route('/')
def home():
    posts = list(db.posting.find({},{'_id':False}))
    #len(posts)
    return render_template('index.html', posting=posts)

# 카테고리 별로 포스팅 목록 가져오기
@app.route('/category/<val>')
def category(val):
    post_cate = list(db.posting.find({'Category':val}, {'_id':False}))
    return render_template('index.html', posting=post_cate, category=val)

# 글 삭제
@app.route('/post_delete', methods=['POST'])
def post_delete():
    ID = request.form['id_give']
    db.posting.delete_one({'ID': int(ID)})
    return jsonify({'result':'success','msg':'삭제 완료'})

# 글 포스팅 하기
@app.route('/post_write', methods=['POST'])
def post_write():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({"username": payload["id"]})

        title_receive = request.form['title_give']
        Category = request.form['category_give']
        author = userinfo['username']
        date = datetime.today().strftime("%Y-%m-%d %H:%M")

        # bs4에 사용하고 저장할 url
        url = request.form['url_give']
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
        data = requests.get(url, headers=headers)
        soup = BeautifulSoup(data.text, 'html.parser')
        try:
            img = soup.select_one('meta[property="og:image"]')['content']
        except:
            img =""


        # 게시글 id 자동증가
        num = db.postid.find_one({},{'_id':False})
        ID = 0
        if num is None:
            doc = {'ID': 0}
            db.postid.insert_one(doc)
        else:
            ID = num['ID'] + 1
            db.postid.update_one({'ID':num['ID']},{'$set':{'ID':ID}})


        # url은 상단에 있음
        comment = request.form['desc_give']
        content = {'img':img, 'url':url,'comment':comment}

        doc = {
            "ID": ID,
            "Category": Category,
            "Title": title_receive,
            "Author": author,
            "Date": date,
            "Content": content,
            "like": 0
        }

        db.posting.insert_one(doc)
        return jsonify({"result": "success"})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


# 상세 페이지 보기
@app.route('/post_view/<ID>')
def post_view(ID):
    load = db.posting.find_one({'ID':int(ID)},{'_id':False})
    # print(load)
    return render_template('detail.html', post=load)


# 쓴글 보기
@app.route('/api/write_post', methods=['GET'])
def write_post():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({'username': payload['id']}, {'_id': 0})
        post = list(db.users.find({'Author':userinfo['username']}, {'_id': False}))

        # html 파일명이 어떻게 될지 몰라 임시지정
        return render_template('mypage.html', posts=post)
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


# 마이페이지
@app.route('/mypage')
def mypage():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({'username': payload['id']}, {'_id': 0})
        posts = list(db.posting.find({'Author':userinfo['username']}, {'_id': False}))
        # print(payload['id'], userinfo['username'])
        # print(posts)
        return render_template('mypage.html', myinfo=userinfo, posting=posts)
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


# 좋아요 +1
@app.route('/like', methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    ID = request.form['id_give']
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({"username": payload['id']}, {"_id": False})

        # 로그인 안한 사람
        if userinfo is None:
            return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

        # 기존 like 수 가져오기
        old_like = db.posting.find_one({'ID': int(ID)}, {'_id': False})
        # print(f'올드 like : {old_like["like"]}')

        # 포스트의 추천버튼 최소 클릭시 실행
        if old_like['like'] == 0:
            doc = {
                'ID': ID,  # 포스트 아이디
                'user': []  # 추천 누른사람
            }
            db.like.insert_one(doc)

        # 누른사람 걸러내기
        like_list = db.like.find_one({'ID': ID}, {'_id': False})
        # print(f"누른사람 : {type(like_list['user'])}")
        for i in like_list['user']:
            if i == userinfo['username']:
                return jsonify({'result': 'fail','msg': '이미 눌렀습니다.'})

        # 누른사람 추가하기
        # print(f"추가할 사람 : {userinfo['username']}")
        db.like.update_one({'ID': ID}, {'$push': {'user': userinfo['username']}})

        # 추천 +1
        new_like = int(old_like['like']) + 1
        db.posting.update_one({'ID': int(ID)}, {'$set': {'like': new_like}})

        return jsonify({"result": "success", 'msg': '좋아요!'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return jsonify({"result": "faill", 'msg': '추천은 로그인 후 사용가능합니다.'})


# 이 밑은 계획에 있었으나 다 완성하지 못 한 구간입니다.
# 읽은 글 보기 (임시 중단)
@app.route('/api/read_post')
def read_post():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({'id': payload['id']}, {'_id': 0})

        return render_template('mypage.html', user=userinfo)
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


# 프로필 보기 (폐기)
@app.route('/user')
def user():
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.users.find_one({'username': payload['id']}, {'_id': False})
        print(userinfo)
        return render_template('mypage.html', user=userinfo)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
