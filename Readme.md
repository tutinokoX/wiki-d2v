# Wikibediaのダンプデータからdoc2vecのモデル作成
doc2vecのモデル作成の学習方法には色々なやり方があり，どれが最善であるかが現段階でわからない．
そのため，前処理と同時にやると前処理の時間だけ学習の時間が長くなるため，前処理と学習を分けて行う．

どちらの，処理でもmysqlを使用しており，使用の際にはmysqlのアカウントが必要になる．
アカウントの作り方は，別の記事に記載 (忘れてなければリンクを付ける)
以下の形式で自分のアカウントを"doc/secret.py"に記載する．
```python
import mysql.connector

def sql_cliant():

    connector = mysql.connector.connect(
        user=[ユーザ名],
        password=[パスワード],
        host=[ホスト名],
        database=[データベース名],
        charset='utf8mb4')

    return connector
```

charasetは，"utf8mb4"に固定する．
wikiダンプデータには，絵文字などの4byte文字列が含まれるため，この設定をする．

## 使用したライブラリ

何入れたか忘れた^^;

とりあえず，pipリスト
```
% pip3 list                                                                                                                                                     
boto (2.48.0)
bz2file (0.98)
click (6.7)
Flask (0.12.2)
gensim (3.0.1)
itsdangerous (0.24)
Jinja2 (2.9.6)
joblib (0.11)
MarkupSafe (1.0)
mecab-python3 (0.7)
mysql-connector-python (8.0.5)
mysql-connector-python-rf (2.2.2)
numpy (1.13.3)
pip (9.0.1)
pyknp (0.3)
requests (2.9.1)
scipy (0.19.1)
setuptools (32.2.0)
six (1.11.0)
smart-open (1.5.3)
Werkzeug (0.12.2)
wheel (0.29.0)
```


## 1. 前処理
ソースファイル
> ./pre_process.py


実行方法
```
# python3 pre_process.py
# python3 -O pre_process.py // デバック時
```


### 概要
前処理では，ダンプデータからの余分な文字，文字列の削除と形態素解析を行う．
形態素解析器には，速度を考慮してMeCabを使用．

wikiのダンプデータは，あらかじめデータベース(MySql)に格納しておく，詳しいやり方は別の記事を参照

前処理したデータは，idと記事タイトルと一緒に，データベースに格納する．上記のタンプデータとは，データベース自体は同一だが，テーブルは変更する．格納するデータは，形態素をカンマ区切りを行ったテキストデータとする．

テーブルの設定とコマンドを以下に示す．データベースは，"mwiki"，テーブル名は，"morpheme_text"
```
mysql> create table mwiki.morpheme_text(morp_id int , morp_title varchar(255) , morp_text MEDIUMTEXT)
mysql> ALTER TABLE mwiki.morpheme_text CONVERT TO CHARACTER SET utf8mb4;
mysql> alter table mwiki.morpheme_text add primary key(morp_id);
mysql> describe mwiki.morpheme_text;
+------------+--------------+------+-----+---------+-------+
| Field      | Type         | Null | Key | Default | Extra |
+------------+--------------+------+-----+---------+-------+
| morp_id    | int(11)      | NO   | PRI | NULL    |       |
| morp_title | varchar(255) | YES  |     | NULL    |       |
| morp_text  | mediumtext   | YES  |     | NULL    |       |
+------------+--------------+------+-----+---------+-------+
```


### 高速化

#### MySqlから取得する際の高速化
通常多くのデータをまとめて取得すると，メモリに乗らなかったり，動作確認が出来なかったりと不自由な点がいくつかある．
そこで．取得範囲を分割することが考えられる．しかし，この際に以下のような方法で行うと処理が遅くなってしまう．
```MySql
mysql> select * from limit [取得範囲] offset [取得位置]
```
offsetの処理は，0から取得位置まで取得してから，いらない部分を消しているらしい．（どっかのサイトに書いてあった．．リンクを見失うというミス．．．）
従って，取得位置が大きくなればなるほど上記の処理は遅くなる．

実際に，最初はこれでダンプデータにアクセスしていて，後半とんでもなく遅くなったのは確認済み．

一度に全部取り出せば．この問題は解決できるが、ダンプデータなので，メモリに乗らないこともあると考えて以下の方法で解決した．

```MySql
mysql> select * from [テーブル名] where morp_id between 10 and 20
```
これで,10から20までの範囲だけを取得できる．

上記の処理を実際に使うには，idの値から一定の範囲を取得しているので，データベースにidを付けておく必要がある．


#### MySqlに格納する際の高速化
格納する際に，複数同時に格納することで同時に格納する数だけ高速化できる．
同時に構築する際には，その分長いsql文を生成する必要があるため，調整が必要

テーブルは，mwiki.morpheme_v3を使用する

実際のコマンド
```mysql
mysql> insert into [テーブル名] (morp_id , morp_title , morp_abstract)
values ("1" , "name_1" , "word_1") , ("2" , "name_2" , "name_2") , ... , ("n" , "name_n" , "word_n")
on duplicate key update morp_title = VALUES(morp_title) , morp_abstract = VALUES(morp_abstract)
```

"values"の後に追加したデータをカンマ区切りで追加することで複数同時に処理することができる．


"on duplicate" から始まる文は，もし同じidだった場合は上書き，違うなら追加する操作である．
この操作を有効にするために，morp_idに対してプライマリー設定を付けておく[プライマリー設定方法](http://phpjavascriptroom.com/?t=mysql&p=autoincerment)
```MySql
mysql> DESCRIBE morpheme_v3;
+---------------+--------------+------+-----+---------+-------+
| Field         | Type         | Null | Key | Default | Extra |
+---------------+--------------+------+-----+---------+-------+
| morp_id       | int(11)      | NO   | PRI | NULL    |       |
| morp_title    | varchar(255) | YES  |     | NULL    |       |
| morp_abstract | text         | YES  |     | NULL    |       |
+---------------+--------------+------+-----+---------+-------+
```

数値をプライマリー（重複）に設定することによりタイトルに関しては，重複してしまうが，他の処理との関係で，wiki
ダンプデータには，同じタイトルだが書かれている内容が異なることがあるため，そこは分けて扱うべきなのでこれでよい．

ここでも，idを与えることによってこのテーブルからデータを受け取る際にも高速化を行うことができるようになる．

#### 並列処理を用いた高速化

コアの数だけ並列処理ができるようにする．
使用したライブラリは，"joblib"

並列処理の際に．mysqlのinsertを含めると，エラーになった．
( おそらく，mysqlでは，一度に同じユーザからのinsertは受け付けないのかな．．．複数のユーザを用意すればあるいわ．．． )

今回は，mysqlに格納するところを並列化するのではなく，
形態素解析，余分文字の削除処理を並列化することにする．

並列化の対象は，ダンプデータから複数の記事を受け取り，複数の記事を並列に処理する．



## 2. 学習

### ソースファイル
> ./model_create.py


### 実行方法
```
# python3 model_create.py
# python3 -O model_create.py // デバック時
```

### 概要
mysqlサーバから学習データをダウンロードする．
ダウンロードしたデータを用いて学習を行う．



## jupyterでの操作

### 実行
```bash
# pwd ~/wiki-d2v/JupyterDir/
# /root/anaconda3/bin/jupyter notebook --allow-root
```
