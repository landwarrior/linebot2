# linebot2

DynamoDB を使った LINE Bot のコードです。

## ローカルでの解析

静的解析用に venv を作り、依存パッケージをインストールします。  
boto3 は Lambda のランタイムに含まれているため、`requirements.txt` には書いてありません。  
解析するときは、venv へ別途インストールします。

```sh
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install boto3 boto3-stubs[dynamodb,events]
```

## Lambda へ上げる zip

環境変数は Lambda 関数の Web 画面上で設定を行っている前提です。

プロジェクト直下で `package_lambda.bat` を実行します。  
このバッチファイルが `package_lambda.ps1` を起動します。

```sh
package_lambda.bat
```

スクリプトは `build/` を作成し、Linux 向けの依存パッケージをそこへインストールします。  
続けて、自作の `.py` を `build/` にコピーし、その中身を `function.zip` にまとめます。  
`lambda_function.py` は zip の直下に入ります。  
`build/` と `function.zip` は Git の管理対象外です。

`package_lambda.ps1` の先頭にある `$LambdaPython` と `$LambdaArch` は、コンソールに表示されているランタイムとアーキテクチャに合わせます。  
arm64 の関数では、`$LambdaArch = "arm64"` にします。

できた `function.zip` を Lambda コンソールからアップロードします。  
ハンドラは `lambda_function.lambda_handler` です。
