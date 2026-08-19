import pandas as pd
def file_reader(file_name):
    try:
        d = pd.read_csv(f"data/{file_name}")

    except FileNotFoundError as e:
        print(e)
        return
    print(d.to_string())

    rows, columns = d.shape
    print(f"total rows equal {rows}")
    print(f"total cols equal {columns}")

    print(f"column names are {list(d.columns)}")
    nulls = d.isnull()
    print(nulls.head().to_string())
    print(f"total missing values {nulls.sum().sum()}")



file_reader("setF.csv")