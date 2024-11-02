import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pywebhdfs.webhdfs import PyWebHdfsClient

class StoresData:
    def read_upload_data_from_csv(self, path_csv, client, path_hdfs):
        df = pd.read_csv(path_csv)
        
        table = pa.Table.from_pandas(df)
        pq.write_table(table, path_hdfs)