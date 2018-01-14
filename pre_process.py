'''
v4からの変更点
・ mysqlを別ファイルで指定
・ ソース整理
'''
import re
import sys
import time
import MeCab
from joblib import Parallel, delayed
from doc import sql_operation


# ######### MeCab ##########

# 形態素解析したデータをリストに格納
def get_surfaces(node):
    words = []
    while node:
        meta = node.feature.split(",")

        if meta[0] == '名詞' or meta[0] == '動詞' or meta[0] == '形容詞':
            if meta[1] != '数':
                word  = node.surface
                words.append(word)
        node = node.next
    return words


# ########## 余分な文字の除去 ##########
# ページ単位での除去
def text_replace(text):


    # text = text.replace('\'', '\'\'')
    text = text.replace('[','')
    text = text.replace(']','')
    text = text.replace('|','')
    text = text.replace(' ','')
    text = text.replace('\'','')
    text = text.replace('（', '(')
    text = text.replace('）', ')')

    # text = re.sub('\{\{Infobox.*\}\}' , '' , text)
    text = re.sub(r"(https?|ftp)(:\/\/[-_\.!~*\'()a-zA-Z0-9;\/?:\@&=\+\$,%#]+)", "" ,text)
    text = re.sub("<ref.*/ref>" , "" ,text)
    text = re.sub("<refname=.*/>" , "" ,text)
    text = re.sub("{{.*}}" , "" ,text)
    text = re.sub("<!-.*-->" , "" , text)
    text = re.sub("^#.*", "", text)

    text = text.replace('/','')
    text = text.replace('\\', '')
    text = text.replace('\"', '')

    return text


# 一行単位での除去
box = 0
def line_replace(line):

    global box

    if(box > 0):
        if(line.find("{") != -1):
            box +=1
        if(line.find("}") != -1):
            box -=1
            return -1
        return -1

    if(line == ""):
        return -1

    if(line.find("{") != -1):
        box = 1
        return -1

    if(line.find("==") != -1):
        return -1

    if(len(line) < 10):
        return -1

    return 0


# ########## リスト変換 ##########
# リスト -> カンマ区切り
def list_to_comma(_list):

    result = ""
    for elem in _list:
        result += elem + ","

    return result

# カンマ区切り -> リスト
def comma_to_list(_comma_str):

    result = []
    for elem in _comma_str.split(","):
        if not elem:
            continue
        result.append(elem)

    return result


# ########## メインプログラム ##########

mecab = MeCab.Tagger ("/usr/local/lib/mecab/dic/mecab-ipadic-neologd")
# 処理しやすい状態に文字列を整形してから形態素解析
def split_into_words(org_text):
    result = []
    count = 0
    global box , mecab
    box = 0

    text = text_replace(org_text)
    lines = text.splitlines()
    # lines = text.split("\n")

    for line in lines:

        if(line_replace(line) == -1):
            continue

        # 1行データから"。"で分割
        for sentence in line.split("。"):
            if(sentence == ""):
                continue

            # print(str(count+1) + " : " + sentence)

            # 形態素解析の処理
            mecab.parse('')
            node = mecab.parseToNode(sentence)
            for word in get_surfaces(node):
                if(word == "") :
                    continue
                result.append(word)

        count+=1

    return result


# 形態素解析子プロセス (並列化のため実装)
def morp_c(row):
    # global ctr ,csr

    num  = int(row[0])
    text = row[2].decode('utf-8')
    name = row[1].decode('utf-8').replace('\"', '\"\"').replace('\\','\\\\') # sqlに格納する際に邪魔な単語を変換

    # 形態素解析 -> リスト
    words = split_into_words(text)

    if not words:
        return

    return {"num":num , "name":name ,"text":words}


# 形態素解析
def morp(rows):

    results = []
    if not __debug__:
        for row in rows:
            results.append(morp_c(row))
    else:
        # 並列処理
        results = Parallel(n_jobs=-1)([delayed(morp_c)(row) for row in rows])

    return results


# mysqlに形態素解析したデータを格納
def into_sql(sql_op , values , LN = 10):
    sets = []
    for result in values:
        if not result:
            continue

        sets.append({"num": result["num"], "name": result["name"], "words": list_to_comma(result["text"])})

        # insert文をまとめて実行
        if (len(sets) >= LN):
            sql_op.insert_abst_mrop_cursor_multi(sets)
            sets.clear()

    # setsの残ったデータを挿入する
    if len(sets) != 0:
        sql_op.insert_abst_mrop_cursor_multi(sets)
        sets.clear()


# 形態素解析したデータをsqlに格納する
# get_offset : ダンプデータの記事の開始位置．この値を変更して，サーバを分散して使うのも可能，その際の終了処理は検討中
# get_limit  : ダンプデータから記事をまとめて受け取る範囲．大きければ，並列処理での恩恵が大きいが，大きすぎるとメモリに乗らないかも...
def morps_into_sql(get_offset = 0, get_limit = 500 , debug_size = 1000):

    # sql操作を設定
    sql_op = sql_operation.MySqlCtr()

    # 最大IDを取得 プログラム進捗確認のため（余裕があれば作成）
    # max_size = 200 # mysqlで確認したサイズ 自動で取得できるけどね．．
    max_size = sql_op.get_last_id()

    while True:
        if not __debug__:
            if(get_offset >= debug_size):
                print(" debug finish")
                break
        else:
            if(get_offset >= max_size):
                print(" all finish")
                break

        csr = sql_op.get_dump_cursor(get_limit, get_offset)
        # csr = get_dump_cursor_des(csr, "ネコ")
        rows = csr.fetchall()
        get_offset += get_limit

        # 形態素解析(並列処理の効果向上のため，まとめて解析)
        morp_datas = morp(rows)

        # mysqlに形態素解析したデータを格納
        into_sql(sql_op , morp_datas)

        sys.stdout.write('\r前処理中 {}/{}'.format(get_offset,max_size))


if __name__ == "__main__":

    s = time.time()

    # データベース -> 形態素解析 -> データベース
    morps_into_sql(get_offset=3155443)

    elapsed = time.time() - s
    print('time: {0} [sec]'.format(elapsed))
