"""
"""

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

from datetime import datetime, timedelta

from hdfs import InsecureClient
from clickhouse_driver import Client
import json
import re

SHEDULE_INTERVAL = '15 * * * *'
hdfs_path = '/opt/gobblin/output/gevorg.hachaturyan'
mem_file_name = '/../semaphore/mem_file'
NOT_WHITESPACE = re.compile(r'[^\s]')

def getMemFile(hdfs_client):
    hdfs_path_exist = hdfs_client.acl_status(hdfs_path + mem_file_name, strict=False)
    if hdfs_path_exist:
        with hdfs_client.read(hdfs_path + mem_file_name) as reader:
            return reader.read().decode("utf-8")
    else: 
        return False

def decode_stacked(document, pos=0, decoder=json.JSONDecoder()):
    while True:
        match = NOT_WHITESPACE.search(document, pos)
        if not match:
            return
        pos = match.start()

        try:
            obj, pos = decoder.raw_decode(document, pos)
        except json.JSONDecodeError:
            raise
        yield obj

def setMemFile(hdfs_client, file_name):
    hdfs_client.write(hdfs_path = hdfs_path + '/' + mem_file_name, data = file_name, overwrite=True)

def uploadFileIntoClickHouse():

    clickhouse_client = Client(host='localhost')
    clickhouse_client.execute('create table if not exists gevorg_hachaturyan (timestamp Float64 , referer String, location String, remoteHost String, partyId String, sessionId String, pageViewId String,eventType String, item_id String, item_price UInt32, item_url  String, basket_price String, detectedDuplicate UInt8, detectedCorruption UInt8, firstInSession UInt8, userAgentName String) ENGINE = Memory')

    hdfs_client = InsecureClient('http://npl-namenode.europe-west1-b.c.npl-lab-project.internal:50070', user='gevorg')
    mem_val = getMemFile(hdfs_client)

    list_of_files = hdfs_client.list(hdfs_path, status=False)
    for file_name in list_of_files:
        if mem_val and file_name <= mem_val:
            continue
        with hdfs_client.read(hdfs_path + '/' + file_name) as reader:
            for one_json_object in decode_stacked(reader.read().decode("utf-8")):
                print('--------------------')
                print(one_json_object)
                print('--------------------')
                clickhouse_client.execute('INSERT INTO gevorg_hachaturyan  VALUES ', [one_json_object])
            setMemFile(hdfs_client, file_name)

default_args = {
    'owner': 'gevorg',
    'depends_on_past': False,
    'start_date': datetime(2019, 3, 13),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='NewProLab_HDFS_TO_ClickHouse', 
    default_args=default_args, 
    schedule_interval=SHEDULE_INTERVAL)

hdfs_test = PythonOperator(
    task_id='hdfs_clickhouse_loader', 
    python_callable=uploadFileIntoClickHouse,
    # provide_context=True, 
    dag=dag)

hdfs_test