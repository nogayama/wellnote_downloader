# wellnote downloader



Wellnote からデータをダウンロードするツールです。ブラウザを自動操作し、ユーザーが一つづつクリックしたのと同じ作業を次々と繰り返すツールです。



必要な環境は、Python が動き、FirefoxまたはChromeがインストールされている環境です。OSは特に指定しません。




## セットアップ

1. Firefox または Chrome をインストールする。
2. Pythonをインストールする。
    コマンドラインから`python3`コマンドと`pip3`コマンドを実行できるか確認する
    ```sh
    $ python3 --version
    Python 3.11.0
    
    $ pip3 --version 
    pip 22.3 from pip (python 3.11)
    ```
3. wellnote downloader をインストール
    ```bash
    pip3 install wellnote_downloader
    ```
    
    コマンドラインから`wellnote_downloader`コマンドを実行できるか確認する。
    ```sh
    $ wellnote_downloader --version
    0.1.0
    ```



## 使い方



### アルバム内の写真・動画のダウンロード



1. 実行前にメールアドレスとパスワードを設定します。
    ```sh
    $ export WELLNOTE_EMAIL=あなたのEmailアドレス
    $ export WELLNOTE_PASSWORD=あなたのパスワード
    ```
2. アルバム内の写真・動画をダウンロードします。2015年の1月から2016年の12月までダウンロードする場合は以下のように実行します。
    ```sh
    $ wellnote_downloader album --start 2015-01  --end 2016-12
    ```

3. 今いるフォルダ内に`download`というフォルダができているので、その中のファイルがダウンロードできているか確認します。



### ホーム画面の日記のダウンロード



TBD



## 開発者

- **Takahide Nogayama** - [Nogayama](https://github.com/nogayama)


## ライセンス

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details

## 貢献方法

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
