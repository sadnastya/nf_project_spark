import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pywebhdfs.webhdfs import PyWebHdfsClient

class StoresData:
    def read_upload_data_from_csv(self, path_csv, sep, hdfs,path_hdfs):
        df = pd.read_csv(path_csv, sep=sep)
        
        table = pa.Table.from_pandas(df)

        buffer = pa.BufferOutputStream()

        pq.write_table(table, buffer)

        parquet_data = buffer.getvalue()
        with hdfs.open_output_stream(path_hdfs) as hdfs_file:
            hdfs_file.write(parquet_data)