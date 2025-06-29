# Rustipy

質素で軽快なcrateホスティングサーバーです。

## 概要

Rustipyは、社内ネットワークやローカル環境での利用に特化した、非常に軽量なRustクレートホスティングサーバーです。Rustのクレートレジストリプロトコル（スパースインデックス）とクレートファイルのダウンロードをサポートしており、特にローカルでのCI/CD環境において効果を発揮します。

## 主な特徴

- オフライン/クローズドネットワーク対応
  - インターネット接続が制限された環境や完全に隔離された環境でも、Rustの依存関係解決を可能にします。主にクローズドな環境でCI/CDを行う必要がある場合に効果を発揮します。
- シンプルなセットアップ
  - 少ない手順でサーバーを起動し、すぐに利用を開始できます。
- プライベートクレートのホスティング
  - 外部に公開したくない独自のRustクレートや内部ツールを、セキュアなローカル環境で共有・管理できます。

## セットアップと実行

Rustipyのセットアップと実行は非常に簡単です。

- クレートファイルの準備:
  - ホストしたい.crateファイル（cargo packageコマンドなどで生成されます）をすべて `./packages` ディレクトリに保存します。

- 依存関係のインストールとサーバーの実行:
  - uv を使用して依存パッケージをインストールし、サーバーを起動します。uv がインストールされていない場合は、pip install uv でインストールできます。
  
```bash
uv sync
uv run uvicorn rustipy:APP --host localhost
```

## API

Rustipyが提供するAPIエンドポイントは以下の通りです。

| endpoint                          | method | response   | 内容                                       |
| --------------------------------- | ------ | ---------- | ------------------------------------------ |
| /                                 | get    | HTML       | インデックスページ                         |
| /sparse/config.json               | get    | json       | sparse INDEXの設定                         |
| /sparse/{aa}/{bb}/{name}          | get    | json       | sparse INDEX                               |
| /crates/{name}/{version}/download | get    | crate file | 特定バージョンのクレートをダウンロードする |
| /api/v1/crates/new                | put    | json       | クレートをアップロードする(cargo publish)  |

## 設定

設定を変えるには起動するディレクトリに以下の内容で`.env`を作成します。

```toml
# .env
host=localhost                              # ホスト
port=8000                                   # ポート
protocol=http                               # プロトコル
package_path=./packages                     # crateファイル保存ディレクトリへのパス
token=your_secret_publish_token_for_rustipy # セキュリティトークン　cargo publishでアップロードする際に必要
```

## rust環境の設定

cargoでローカルに立てたインデックスからパッケージをビルドするには、`.cargo/config.toml`で`registries`にレジストリの設定を追加し、依存パッケージで設定したレジストリを指定します。

以下に設定を例示します。

### `.cargo/config.toml`

```toml
[registries.local-regist]
index = "sparse+http://localhost:8000/sparse/"

token = "your_secret_publish_token_for_rustipy"   # クレートをアップロードするときには、`.env`で設定したトークンが必要
```

### `Cargo.toml`

```toml
[package]
name = "sample"
version = "0.1.0"
edition = "2024"
publish = ["local-regist"]    # クレートをアップロードする際には必要

[dependencies]
ferris-says = {version = "*", registry ="local-regist"}
```

正しく設定された場合は以下のように普通のコマンドでビルドとクレートのアップロードができる。

```bash
cargo build
cargo publish
```
