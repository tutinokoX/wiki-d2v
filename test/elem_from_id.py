

from doc import sql_operation

def main(id = 10):

    sql_op = sql_operation.MySqlCtr()

    '''
    print('文字列入力:')
    search_str = input()
    '''

    csr = sql_op.show_elem_id(id)
    rows = csr.fetchall()

    print("id : ====================")
    print(rows[0][0])
    print("name : =====================")
    print(rows[0][1])
    print("words : ====================")
    print(rows[0][2])


if __name__ == "__main__":

    main(100)