from doc import secret



########## MySql ##########

class MySqlCtr:
    def __init__(self):
        self.table = "mwiki.morpheme_text"
        self.connector = secret.sql_cliant()
        self.cursor = self.connector.cursor()

    def __del__(self):
        self.cursor.close
        self.connector.close


    # 開始位置の指定してカーソル更新
        # wikiページのダンプデータ , ページタイトル
    def get_dump_cursor(self, limit, offset):

        mysql_order = "select r.rev_page , p.page_title , t.old_text from " \
                      "mwiki.page as p , mwiki.text as t , mwiki.revision as r where" \
                      " p.page_id=r.rev_page AND t.old_id=r.rev_text_id"
        mysql_order += " AND r.rev_page BETWEEN "
        mysql_order += str(offset)
        mysql_order += " AND " + str(offset+limit)

        # print(mysql_order)

        self.cursor.execute(mysql_order)
        return self.cursor


    def get_dump_cursor_des(self, word):
        mysql_order = "select p.page_title , t.old_text from " \
                      "mwiki.page as p , mwiki.text as t , mwiki.revision as r where " \
                      "p.page_id=r.rev_page AND t.old_id=r.rev_text_id"
        mysql_order += " AND p.page_title IN(\"" + word + "\")"

        # print(mysql_order)

        self.cursor.execute(mysql_order)
        return self.cursor


        # アブストラクトの形態素 , ページタイトル
    def get_abst_mrop_cursor(self , limit , offset):

        mysql_order = "select morp_title , morp_text"
        mysql_order += " from " + self.table
        mysql_order += " limit " + str(limit)
        mysql_order += " offset " + str(offset)

        self.cursor.execute(mysql_order)
        return self.cursor


    # データの挿入
        # アブストラクトの形態素 ，ページタイトル
    def insert_abst_mrop_cursor(self , name , words):

        mysql_order = "insert"
        mysql_order += " into " + self.table
        mysql_order += " (morp_title , morp_text)"
        mysql_order += " values( \"" + name + "\" , \"" + words + "\") "
        mysql_order += " on duplicate key update"
        mysql_order += " morp_title= \"" + name + "\" "
        mysql_order += " , morp_text= \"" + words + "\" "

        # print(mysql_order)

        self.cursor.execute(mysql_order)
        self.connector.commit()

    def insert_abst_mrop_cursor_multi(self, sets):

        mysql_order = "insert"
        mysql_order += " into " + self.table
        mysql_order += " ( morp_id , morp_title , morp_text)"
        mysql_order += " values"

        mysql_order += " (\"" + str(sets[0]["num"]) + "\" , \"" + sets[0]["name"] + "\" , \"" + sets[0]["words"] + "\")"
        for i in range(1 , len(sets)):
            mysql_order += " , (\"" + str(sets[i]["num"]) + "\" , \"" + sets[i]["name"] + "\" , \"" + sets[i]["words"] + "\")"

        mysql_order += " on duplicate key update"
        mysql_order += " morp_title = VALUES(morp_title)"
        mysql_order += " , morp_text = VALUES(morp_text)"

        #print(mysql_order)
        # print( len(sets[0]["words"].encode('utf-8') ))

        if(len(sets[0]["words"].encode('utf-8') ) > 16777215):
            print("insert err : over MEDIUMBLOB ") # これより大きい型 : LONGTEXT
            return

        try:
            self.cursor.execute(mysql_order)
            self.connector.commit()

        except:
            print("insert err (err ids) : ")
            for set in sets:
                print(" > " + format( set["num"]) )
            pass

        return

    def get_text_mrop_cursor_between(self, limit, offset):

        mysql_order = "select morp_id , morp_title , morp_text"
        mysql_order += " from " + self.table
        mysql_order += " where morp_id BETWEEN "
        mysql_order += str(offset)
        mysql_order += " AND " + str(offset + limit)

        self.cursor.execute(mysql_order)
        return self.cursor


    def get_last_id(self):
        mysql_order = "select page_id from mwiki.page order by page_id desc limit 1"

        self.cursor.execute(mysql_order)
        rows = self.cursor.fetchall()

        return rows[0][0]

    def show_elem_id(self , id):

        mysql_order = "select " \
                      "* from "
        mysql_order += self.table
        mysql_order += " WHERE morp_id IN(" + format(id) + ")"

        self.cursor.execute(mysql_order)
        return self.cursor