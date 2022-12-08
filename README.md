# Wellnote Downloader



Wellnote からデータをダウンロードするツールです。ブラウザを自動操作し、ユーザーが一つづつクリックしたのと同じ作業を次々と繰り返すツールです。



**wellnoteのサーバーに過度な負荷がかかることが予見される使い方（ツールを改造したり、並列でいくつも起動したりするなど）は絶対にやめてください。** サーバーが落ちると、全員がダウンロードできなくなります。それにそのまま早期にサービス終了する可能性もありますので、常識の範囲内での利用をお願いします。



[![Wellnote Downloader アルバムから写真・動画をダウンロード](https://user-images.githubusercontent.com/11750755/206524695-38bffc61-b4ac-4802-a810-13b8cc824e83.png)](https://youtu.be/o0UrRwXwCeI)

----



> 実行例の見方： この文書で例示する実行例では、実行するコマンドを、`$`の後ろに書きます。続く行で実行結果の例を示しています。例えばファイル`a.txt`と`b.txt`が存在するフォルダで`ls`コマンドを実行すると２つのファイル名が表示されますが、その実行例は次のように示します。
>
> ```
> $ ls
> a.txt b.txt



## セットアップ



必要な環境は、コマンドターミナルがあり、Python が動き、FirefoxまたはChromeがインストールされている環境です。OSは特に指定しません。



1. Firefox または Chrome をインストールする。
2. Pythonをインストールする。
    コマンドラインから`python3`コマンドと`pip3`コマンドを実行できるか確認する
    
    ```sh
    $ python3 --version
    Python 3.11.0
    
    $ pip3 --version 
    pip 22.3 from pip (python 3.11)
    ```
3. Wellnote Downloader をインストール
    ```bash
    $ pip3 install wellnote_downloader
    長いので略
    ```
    
    コマンドラインから`wellnote_downloader`コマンドを実行できるか確認する。
    ```sh
    $ wellnote_downloader album --help
    usage: wellnote_downloader [-h] {album} ...
    
    Wellnote Downloader
    
    positional arguments:
      {album}     sub commands
        album     download album
    
    options:
      -h, --help  show this help message and exit
    
    ```



## 使い方



### アルバム内の写真・動画のダウンロード



1. アルバム内の写真・動画をダウンロードします。2015年の1月から2016年の12月までダウンロードする場合は以下のように実行します。
    ```sh
    $ wellnote_downloader album --start 2015-01  --end 2016-12
    ```

2. 今いるフォルダ内に`download`というフォルダができているので、その中のファイルがダウンロードできているか確認します。






- Tips

    1. 実行前にメールアドレスとパスワードを設定すると、入力を省略できます。
        ```sh
        $ export WELLNOTE_EMAIL=あなたのEmailアドレス
        $ export WELLNOTE_PASSWORD=あなたのパスワード
        ```



### ホーム画面の日記のダウンロード



TBD



## 開発者

- [Takahide Nogayama](https://github.com/nogayama)

## ライセンス

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details



## 貢献方法

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
