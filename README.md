# Django RLS 多租戶隔離專案文件

本資料夾包含 Django RLS 多租戶隔離專案的完整文件。

## 快速開始

如果是第一次使用本專案，請先閱讀：

- **[QuickStart.md](docs/QuickStart.md)**

## 文件結構

### 核心文件

- **[RLS\_完整說明文件.md](docs/RLS_完整說明文件.md)** - 完整的 RLS 技術說明文件

### 操作指南

- **[QuickStart.md](docs/QuickStart.md)** - 快速啟動 RLS 多租戶

- **[SQL-test-tutorial.md](docs/SQL-test-tutorial.md)** - SQL 測試操作手冊

- **[test-tenant-tutorial.md](docs/test-tenant-tutorial.md)** - 租戶隔離測試

## 相關測試工具

### 測試腳本

- **[test_rls.sql](scripts/test_rls.sql)** - SQL 測試腳本

  - 完整的 RLS 隔離測試
  - 政策驗證測試
  - 邊界條件測試

- **[test_tenant_isolation.py](tenants/management/commands/test_tenant_isolation.py)** - Django 管理命令測試
  - 自動化測試腳本
  - 完整的隔離測試套件
  - 測試結果報告

### 配置文件

- **[test_config.env](config/test_config.env)** - 測試環境配置
- **[docker-compose.yaml](config/docker-compose.yaml)** - Docker 容器配置
- **[init.sql](scripts/init.sql)** - 資料庫初始化腳本

## **專案結構：**

```
django-rls-multitenant/
├── config/                         # 配置檔案
│   ├── docker-compose.yaml         # Docker 配置
│   └── test_config.env             # 測試配置
├── docs/                           # 文件目錄
│   ├── QuickStart.md               # 快速入門指南 (推薦)
│   ├── RLS_完整說明文件.md          # 核心技術文件
│   ├── SQL-test-tutorial.md        # SQL 測試指南
│   └── test-tenant-tutorial.md     # 測試教程
├── logs/                           # 日誌檔案
│   └── django.log                  # Django 日誌
├── scripts/                        # 腳本檔案
│   ├── init.sql                    # 資料庫初始化
│   └── test_rls.sql                # SQL 測試腳本
├── tenants/                        # Django 應用程式
│   └── management/commands/
│       └── test_tenant_isolation.py # 測試命令
├── tests/                          # 測試目錄
└── README.md                       # 專案說明文件
```
