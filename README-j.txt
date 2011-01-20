w3m-2chpy.cgi は、w3m の local CGI 機能を利用して、w3m を２ちゃんねるブラウザとして使えるようにするスクリプトです。
w3m-2ch.cgi (http://www.geocities.jp/smug5680/) の代替を目指して開発されています。


=== 動作環境 ===
w3m (Local CGI 機能付き)
Python (ver 2.5.2 以上。Python3には未対応)


=== インストール ===
w3m-2chpy.cgi を local CGI スクリプトが起動できるディレクトリに置いてください(w3m の local CGI については http://w3m.sourceforge.net/MANUAL.ja.html#LocalCGI 参照)。
例えば、~/cgi-bin ディレクトリを local CGI 置き場にする場合
(1) ~/cgi-bin ディレクトリに w3m-2chpy.cgi をコピー
(2) w3m の設定ファイル(ex: ~/.w3m/config)を開いて、cgi_bin の行を次のように書き換える(無ければ追加する)
cgi_bin ~/cgi-bin
(3) 添付した bookmark.html を w3m で開いて、リンクから飛ぶ
で使用できるはずです。
w3m-2chpy.cgi はファイル置き場として ~/.w3m/.w3m-2ch/ ディレクトリを使用します(変更したい場合は w3m-2chpy.cgi の cache_dir 変数の値を書き換えてください)。


=== 機能 ===
板一覧表示
ヘッドライン表示
スレッド一覧表示
スレッド表示
（過去ログ表示）
書き込み


=== 開発動機 ===
メインマシンを MacBook Air に換えたら、w3m-2ch.cgi が動かなかった:)


