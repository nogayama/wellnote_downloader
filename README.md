# Wellnote Downloader



[Wellnote Downloader](https://github.com/nogayama/wellnote_downloader)  は、Wellnote からデータをダウンロードするツールです。ブラウザを自動操作し、ユーザーが一つづつクリックしたのと同じ作業を次々と繰り返すツールです。



↓動作の様子
[![Wellnote Downloader アルバムから写真・動画をダウンロード](https://user-images.githubusercontent.com/11750755/206524695-38bffc61-b4ac-4802-a810-13b8cc824e83.png)](https://youtu.be/o0UrRwXwCeI)
[![Wellnote Downloader を使ってホームの日記を画像としてダウンロード(コメント、スタンプ付き)](https://user-images.githubusercontent.com/11750755/206735482-b98ea332-9126-4b4f-aa47-bd6e67f76be3.png)](https://youtu.be/RyJrXGKGksc)

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
    $ wellnote_downloader --version
    0.10.0
    
    # Command not found エラーが出る場合は、`wellnote_downloader` を `python -m wellnote_downloader` にすると動くかもしれません
    $ python -m wellnote_downloader --version
    
    ```



## 使い方



### アルバム内の写真・動画のダウンロード

1. 全部ダウンロードする場合

    ```sh
    $ wellnote_downloader album
    ```

2. 2015年の1月から2016年の12月までダウンロードする場合は以下のように実行します。

    ```sh
    $ wellnote_downloader album --start 2015-01  --end 2016-12
    ```

    

3. 今いるフォルダ内に`Downloads`というフォルダができているので、その中のファイルがダウンロードできているか確認します。



### ホーム画面の日記のダウンロード（コメント、スタンプ付き）


1. 全部ダウンロードする場合

    ```sh
    $ wellnote_downloader home
    ```


2. 2015年の1月から2016年の12月までダウンロードする場合は以下のように実行します。

    ```sh
    $ wellnote_downloader home --start 2015-01  --end 2016-12
    ```

    

3. 今いるフォルダ内に`Downloads`というフォルダができているので、その中のファイルがダウンロードできているか確認します。



## その他



**wellnoteのサーバーに過度な負荷がかかることが予見される使い方（ツールを改造してスピード調節部分を削除したり、並列でいくつも起動したりするなど）は絶対にやめてください。** サーバーが落ちると、全員がダウンロードできなくなります。それにそのまま早期にサービス終了する可能性もありますので、常識の範囲内での利用をお願いします。

- 途中で止める場合は、ターミナルウィンドウで`Ctrl-C`を押します。

- 実行前にメールアドレスとパスワードを設定すると、入力を省略できます。
    ```sh
    $ export WELLNOTE_EMAIL=あなたのEmailアドレス
    $ export WELLNOTE_PASSWORD=あなたのパスワード
    ```

- デフォルトではログインセッションを再利用するので、ユーザーを切り替えたくてもログインプロンプトがでないため切り替えられなくなってしまいます。その場合は一度 `--clear-profile`オプションをつけて実行して下さい。

    ```sh
    $ wellnote_downloader home --clear-profile
    $ wellnote_downloader album --clear-profile
    ```

- 画像の読み込みが遅すぎて日記の保存に間に合わないとき、ブラウザを操作するペースを遅くする事ができます。操作イベントを送る前に待つ時間をデフォルトの`1秒`から`3秒`に変えるには、以下のようにします。
    
    ```sh
    $ wellnote_downloader home --interval 3
    ```
    
    
    
- Command not found エラーが出る場合は、`wellnote_downloader` を `python -m wellnote_downloader` にすると動くかもしれません

    ```sh
    $ python -m wellnote_downloader --version
    0.10.0
    ```

    

## 開発者

- [Takahide Nogayama](https://github.com/nogayama)

## ライセンス

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details



## 貢献方法

Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.
