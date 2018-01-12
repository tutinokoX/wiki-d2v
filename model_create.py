

from doc import sql_operation
import pre_process

import sys
from gensim import models
from gensim.models.doc2vec import LabeledSentence
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import collections
import multiprocessing

PASSING_PRECISION = 93

def removal_topic(name , words):
    if (len(words) < 300):
        return True

    if (name.find("削除依頼") != -1):
        return True

    return False


def sentence_create(offset = 0 , limit = 500 , _range = 10000 ):

    # sql操作を設定
    sql_op = sql_operation.MySqlCtr()

    print("sentence_create")
    while True:

        if not __debug__:
            if(offset >= _range):
                print(" break")
                break

        csr = sql_op.get_text_mrop_cursor_between(limit, offset)
        rows = csr.fetchall()
        offset += limit

        # mysqlからの取得データがからなら終了
        if not rows:
            print(" finish")
            break

        for row in rows:
            words = pre_process.comma_to_list(row[2])
            name = row[1]
            num  = int(row[0])
            if(removal_topic(name,words)):
                continue
            # print("num : " + str(num) + " , words : " + row[2])
            # yield TaggedDocument(words=words, tags=[num])
            yield LabeledSentence(words=words, tags=[num])

        sys.stdout.write('\r学習データ取得中 {}'.format(offset))


def rank_conf(model , sentences):
    ranks = []
    for doc_id in range(100):
        inferred_vector = model.infer_vector(sentences[doc_id].words)
        sims = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs))
        rank = [docid for docid, sim in sims].index(sentences[doc_id].tags[0])
        ranks.append(rank)
    print(collections.Counter(ranks))
    if collections.Counter(ranks)[0] >= PASSING_PRECISION:
        return True

    return False


def train(sentences):
    cores = multiprocessing.cpu_count()
    print("cores : " + format(cores))

    model = models.Doc2Vec(size=400, alpha=0.0015, sample=1e-4, min_count=5, workers=cores)
    model.build_vocab(sentences)
    print("model.corpus_count : " + format(model.corpus_count))

    for x in range(30):
        model.train(sentences,total_examples=model.corpus_count, epochs=model.iter)
        print(x)
        if (x > 2):
            if (rank_conf(model , sentences)):
                break

    return model



def main():

    sentences = list(sentence_create())

    print()
    model = train(sentences)
    model.save("./model/2018_0113_doc2vec.model")


if __name__ == '__main__':
    main()
