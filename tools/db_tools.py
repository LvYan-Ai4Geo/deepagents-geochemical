# 加载配置文件，python 》 mysql
import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv


from langchain_core.tools import tool
from mysql.connector import connect, Error

from api.monitor import monitor

load_dotenv(find_dotenv())

def get_db_config()->dict:
    """从外部env文件中获取到数据库的配置信息"""
    config = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT','3306')),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': os.getenv('MYSQL_CHARSET','utf8mb4'),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True,
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL")
    }

    # 过滤空值，也就是没有的过滤掉，上述是默认配置
    config = {k:v for k,v in config.items() if v is not None}

    # 补充，核心配置user  password  database是否存在
    keys = ['user','password','database']
    validate = [key for key in keys if key not in config]
    if validate:
        raise ValueError(f'数据库缺少核心配置：{','.join(validate)}')

    return config


@tool
def list_tables_name()->str:
    """该项工具旨在列举数据库中的表名"""

    # 埋点
    monitor.report_tool(tool_name='数据库中的表名查询工具：list_tables_name')

    # 加载配置
    config = get_db_config()

    with connect(**config) as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute('SHOW TABLES') # 执行sql语句
                rows = cursor.fetchall() # 获取结果  >>> [(),()]，目标结果[表1，表2]
                if not rows:
                    return '没有可用的表'
                result = [row[0] for row in rows]
                return f'可用表{','.join(result)}'

            except Error as e:
                return f'异常信息：{str(e)}'

@tool
def get_table_data(table_name:str):
    """
        查询指定表名的数据！当前工具调用之前，必须先调用list_sql_tables完成表名的校验！
        此工具的作用：1.可以完成单表数据的查询 2. 可以为多表查询提供表结果信息（列名&数据格式）
        :param table_name: 表名
        :return: csv格式的数据（模拟表格数据格式）
                 1.第一行是列信息，列之间使用,（英文的逗号）分割
                 2.第二行开始是表数据，值之间也使用,(英文的逗号)分割
                 3.行和行之间使用\n分割
                 4.至多表数据查询100条
                 例如：
                    id,name,age\n -> 列头
                    1,张三,18\n
                    1,张三,18\n    -> 至多查询100条
                    1,张三,18\n
                    1,张三,18\n
    """
    monitor.report_tool(tool_name='数据库中的单表数据查询工具：get_table_data')

    config = get_db_config()

    with connect(**config) as conn:
        with conn.cursor() as cursor:
            try:
                sql = f"select * from `{table_name}` limit 100"
                cursor.execute(sql) # 执行语句
                results = cursor.fetchall() #>>[(),()],每一个（）是完整的一行数据
                # 要拿到列名
                if not results:
                    return f'数据表{table_name}没有数据'
                columns = cursor.description #>>> [(id,说明),()]
                columns = [row[0] for row in columns]

                # 拿到具体的数据
                result = [','.join(map(str,row)) for row in results]

                header_columns = ','.join(columns)
                data = '\n'.join(result)
                return f'{header_columns}\n{data}'
            except Error as e:
                return f'异常信息：{str(e)}'


@tool
def execute_sql_query(query)->str:
    """
    执行自定义查询sql语句！切记：执行之前，需要通过执行 list_sql_tables明确表名！执行get_table_data
    明确表结构和数据格式！
    :param query: 要执行的自定义sql语句
    :return: csv格式的数据（模拟表格数据格式）
             1.第一行是列信息，列之间使用,（英文的逗号）分割
             2.第二行开始是表数据，值之间也使用,(英文的逗号)分割
             3.行和行之间使用\n分割
             4.至多表数据查询100条
             例如：
                id,name,age\n -> 列头
                1,张三,18\n
                1,张三,18\n    -> 至多查询100条
                1,张三,18\n
                1,张三,18\n
    """
    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="数据库表数据查询工具：execute_sql_query", args={"query":query})

    # 获取数据库参数
    config = get_db_config()
    # 1. 创建一个链接
    # 2. 创建cursor
    # 3. cursor执行sql语句
    # 4. cursor获取返回结果
    # 5. 释放连接和cursor资源
    # 确保要捕捉异常信息，返回异常提示，避免直接报错！
    try:
        # 1. 创建一个链接
        with connect(**config) as  conn:
            # 2. 创建cursor
            with conn.cursor() as cursor:
                # 3. cursor执行sql语句
                cursor.execute(query)
                # 4. cursor获取返回结果
                # 4.1 获取列的信息
                # 返回的查询结果的列的信息
                # description => [(id,列长度...),(),()]
                # 如果查询没有结果 -》 description 也是None
                description = cursor.description
                if not description:
                    return f"执行自定义SQL语句查询没有结果，sql为：{query}！"
                # 4.2 获取查询结果
                # description =>  [(id,列长度...),(date,....),()] => 元组 index = 0 列名
                # [列1,列2,列3...]
                columns = [ desc[0] for desc in description ] # [1,2,3,4]
                # 表数据
                # [(1,张三),(2,李四),(3,二狗子)]
                rows = cursor.fetchall()
                # (1,张三) -> ('1','张三') -> '1,张三'
                # ['1,张三','1,张三','1,张三','1,张三','1,张三']
                results = [ ",".join(map(str,row)) for row in rows]

                # columns -> csv -> header
                # id,name,age
                header_str = ",".join(columns)
                # '1,张三'\n
                data_str = "\n".join(results)

                # 2. 新增：将相同内容保存为 CSV 文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}_data.csv"
                os.makedirs("./exports", exist_ok=True)
                filepath = f"./exports/{filename}"

                with open(filepath, 'w', encoding='utf-8-sig') as f:
                    f.write(f"{header_str}\n{data_str}")

                return f"{header_str}\n{data_str}"
    except Error as e:
        return f"查询出现异常：{str(e)}"


if __name__ == '__main__':
    result = list_tables_name()
    print(result)
    result = execute_sql_query(f"select * from `bishe-total_data` limit 100")
    print(result)