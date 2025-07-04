# Rustipy

A simple and lightweight crate hosting server.

## Overview

Rustipy is an extremely lightweight Rust crate hosting server specialized for use within internal networks and local environments. It supports Rust's crate registry protocol (sparse index) and crate file downloads, proving particularly effective in local CI/CD environments.

## Key Features

* **Offline/Closed Network Support**
    Enables Rust dependency resolution in environments with restricted internet access or completely isolated networks. This is especially effective when CI/CD needs to be performed in a closed environment.
* **Simple Setup**
    Start the server and begin using it immediately with minimal steps.
* **Private Crate Hosting**
    Allows you to share and manage your own Rust crates and internal tools that you don't want to expose publicly, all within a secure local environment.

## Setup and Execution

Setting up and running Rustipy is very straightforward.

* **Prepare Crate Files:**
    Place all `.crate` files you wish to host (generated by commands like `cargo package`) into the `./packages` directory.

* **Install Dependencies and Run the Server:**
    Use `uv` to install dependencies and start the server. If `uv` is not installed, you can install it with `pip install uv`.

```bash
uv sync
uv run uvicorn rustipy:APP --host localhost
```

## API

Rustipy provides the following API endpoints:

| endpoint                          | method | response   | Description                             |
| --------------------------------- | ------ | ---------- | --------------------------------------- |
| /                                 | get    | HTML       | Index page                              |
| /sparse/config.json               | get    | json       | Sparse INDEX configuration              |
| /sparse/{aa}/{bb}/{name}          | get    | json       | sparse INDEX                            |
| /crates/{name}/{version}/download | get    | crate file | Downloads a specific version of a crate |
| /api/v1/crates/new                | put    | json       | Uploads a crate (for cargo publish)     |

## Configuration

To change the settings, create a `.env` file with the following content in the directory where you launch the server:
Ini, TOML

```toml
# .env
host=localhost                              
port=8000                                   
protocol=http                               
package_path=./packages                     # Path to the directory for storing crate files
token=your_secret_publish_token_for_rustipy # Security token required when uploading crates with cargo publish
```

## Rust Environment Setup

To build packages from a locally hosted index using Cargo, you need to add the registry configuration to .cargo/config.toml and specify the configured registry in your dependencies.

Below is an example configuration:


### `.cargo/config.toml`

```toml
[registries.local-regist]
index = "sparse+http://localhost:8000/sparse/"

token = "your_secret_publish_token_for_rustipy"    # The token configured in .env is required when uploading crates
```

### `Cargo.toml`

```toml
[package]
name = "sample"
version = "0.1.0"
edition = "2024"
publish = ["local-regist"]    # Required when uploading crates

[dependencies]
ferris-says = {version = "*", registry ="local-regist"}
```

If configured correctly, you can build and publish crates using regular commands as follows:

```bash
cargo build
cargo publish
```
