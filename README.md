# linebot2

DynamoDBを使ったLINE Botの本格的なコードにしたいやつ

以下のようなコマンドを実行して pip install する

```sh
py -m pip install -r requirements.txt -t .
```

ローカル環境では venv 環境を準備して同じように pip install すればいい。  
ただし、 boto3 等の AWS Lambda 固有のパッケージが見つからないと出てしまうので、以下のコマンドで venv にも pip install を行う。

```sh
pip install boto3 boto3-stubs[dynamodb,events]
```
