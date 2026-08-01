# 将本地开发数据库（backend/.env 的 DB_URL）完整导入 Docker MySQL 容器
#
# 背景：Docker 部署时 MySQL 是全新空库（mysql_data 卷），只自动初始化了
#       mbti_types 16 条，无任何业务数据。本脚本一键把本地库的用户/书籍/
#       评论等数据迁移到容器，避免手工 mysqldump 遇到 Windows GBK 编码坑。
#
# 用法（backend 目录）：
#   python scripts/import_local_data_to_docker.py
#     --container mbookti-mysql-1            # 目标容器名（默认自动探测）
#     --container-password 你的root密码       # 容器 MySQL root 密码
#     [--include-mbti]                       # 连 mbti_types 一起导入（默认跳过，容器已初始化）
#     [--dry-run]                            # 只打印将执行的命令，不真正导入
#
# 注意：
#   1. 依赖 mysqldump（本地 MySQL 自带）。Windows 下自动探测常见安装路径。
#   2. 幂等性：目标库已有数据的表会因主键冲突报错。请先确认目标库为空，
#      或用 --include-mbti 时目标库 mbti_types 也为空。
#   3. 中文数据全程按 utf8mb4 二进制流传输，不受 Windows GBK 控制台影响。
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# Windows 常见 mysqldump 安装路径（探测用）
MYSQLDUMP_CANDIDATES = [
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump",
    r"C:\xampp\mysql\bin\mysqldump.exe",
    r"C:\laragon\bin\mysql\mysql-8.0\bin\mysqldump.exe",
]


def find_mysqldump() -> str:
    """查找 mysqldump：优先 PATH，其次常见 Windows 路径"""
    found = shutil.which("mysqldump")
    if found:
        return found
    for p in MYSQLDUMP_CANDIDATES:
        if Path(p).exists():
            return p
    raise FileNotFoundError(
        "未找到 mysqldump。请安装 MySQL 客户端，或将其加入 PATH。"
    )


def parse_db_url(url: str) -> dict:
    """解析 mysql+asyncmy://user:pass@host:port/db?params 格式"""
    m = re.match(r"mysql\+asyncmy://([^:]+):([^@]+)@([^:/]+):(\d+)/([^?]+)", url)
    if not m:
        raise ValueError(f"无法解析 DB_URL: {url}")
    user, password, host, port, db = m.groups()
    return {"user": user, "password": password, "host": host, "port": int(port), "db": db}


def read_local_config() -> dict:
    """从 backend/.env 读取 DB_URL 并解析出本地库连接信息"""
    if not ENV_FILE.exists():
        raise FileNotFoundError(f"未找到 {ENV_FILE}，请确认在 backend 目录运行")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DB_URL="):
            return parse_db_url(line.split("=", 1)[1])
    raise ValueError(f"{ENV_FILE} 中未找到 DB_URL")


def find_container() -> str:
    """探测正在运行的 mbookti-mysql 容器名"""
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    names = r.stdout.splitlines()
    for n in names:
        if "mysql" in n and "mbookti" in n:
            return n
    # 兜底：只要含 mysql 的 mbookti 容器
    for n in names:
        if "mysql" in n:
            return n
    raise RuntimeError(f"未找到运行中的 MySQL 容器（当前容器: {names}）")


def dump_local(local: dict, mysqldump: str, exclude_mbti: bool) -> bytes:
    """dump 本地库为 utf8mb4 二进制流。关键：--default-character-set=utf8mb4，
    Windows 本地 MySQL 默认 character_set_client=gbk，不加会导出乱码。"""
    cmd = [
        mysqldump,
        f"--user={local['user']}",
        f"--password={local['password']}",
        f"--host={local['host']}",
        f"--port={local['port']}",
        "--databases", local["db"],
        "--single-transaction",
        "--no-tablespaces",
        "--skip-lock-tables",
        "--default-character-set=utf8mb4",
    ]
    if exclude_mbti:
        cmd.append(f"--ignore-table={local['db']}.mbti_types")
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"mysqldump 失败 (exit={r.returncode}): "
            f"{r.stderr.decode('utf-8', errors='replace')[:800]}"
        )
    return r.stdout


def strip_db_statements(sql: bytes) -> bytes:
    """去掉 CREATE DATABASE / USE 语句（目标容器库已存在）"""
    text = sql.decode("utf-8", errors="replace")
    lines = [
        l for l in text.splitlines()
        if not l.strip().upper().startswith(("CREATE DATABASE", "USE `"))
    ]
    return ("\n".join(lines)).encode("utf-8")


def import_to_container(container: str, container_password: str, sql: bytes, dry_run: bool) -> None:
    """把 SQL 复制进容器并导入"""
    tmp = Path(tempfile.gettempdir()) / "mbookti_import.sql"
    tmp.write_bytes(sql)

    if dry_run:
        print(f"[dry-run] docker cp {tmp} {container}:/tmp/mbookti_import.sql")
        print(
            f"[dry-run] docker exec {container} mysql -uroot -p*** "
            f"--default-character-set=utf8mb4 mbookti < /tmp/mbookti_import.sql"
        )
        return

    cp = subprocess.run(["docker", "cp", str(tmp), f"{container}:/tmp/mbookti_import.sql"])
    if cp.returncode != 0:
        raise RuntimeError(f"docker cp 失败 (exit={cp.returncode})")

    inner = (
        f"mysql -uroot -p{container_password} --default-character-set=utf8mb4 "
        f"mbookti < /tmp/mbookti_import.sql"
    )
    ex = subprocess.run(
        ["docker", "exec", container, "sh", "-c", inner],
        capture_output=True,
    )
    if ex.returncode != 0:
        err = ex.stderr.decode("utf-8", errors="replace")
        if "ERROR 1062" in err or "Duplicate entry" in err:
            print("[警告] 导入有主键冲突（目标库可能已有数据），请检查输出。")
        raise RuntimeError(f"导入失败 (exit={ex.returncode}): {err[:800]}")

    # 清理容器内临时文件
    subprocess.run(
        ["docker", "exec", container, "rm", "-f", "/tmp/mbookti_import.sql"],
        capture_output=True,
    )


def verify_counts(container: str, container_password: str) -> None:
    """验证导入后的数据量"""
    sql = (
        "SELECT CONCAT('users=', COUNT(*)) FROM users "
        "UNION ALL SELECT CONCAT('books=', COUNT(*)) FROM books "
        "UNION ALL SELECT CONCAT('mbti_types=', COUNT(*)) FROM mbti_types "
        "UNION ALL SELECT CONCAT('comments=', COUNT(*)) FROM comments"
    )
    r = subprocess.run(
        ["docker", "exec", container, "mysql", "-uroot", f"-p{container_password}",
         "-D", "mbookti", "-N", "-e", sql],
        capture_output=True,
    )
    if r.returncode == 0:
        print("=== 导入后数据量 ===")
        print(r.stdout.decode("utf-8", errors="replace"))
    else:
        print("[提示] 无法验证数据量（仅查询失败，不影响导入结果）")


def main():
    parser = argparse.ArgumentParser(description="导入本地 MySQL 数据到 Docker 容器")
    parser.add_argument("--container", default=None, help="目标容器名（默认自动探测）")
    parser.add_argument("--container-password", default=None,
                        help="容器 MySQL root 密码（必填；或设环境变量 MYSQL_ROOT_PASSWORD）")
    parser.add_argument("--include-mbti", action="store_true",
                        help="连 mbti_types 一起导入（默认跳过）")
    parser.add_argument("--dry-run", action="store_true", help="只打印命令不执行")
    args = parser.parse_args()

    # 容器密码：参数 > 环境变量
    password = args.container_password or __import__("os").environ.get("MYSQL_ROOT_PASSWORD")
    if not password:
        parser.error("缺少容器密码：请用 --container-password 或设置环境变量 MYSQL_ROOT_PASSWORD")

    container = args.container or find_container()
    local = read_local_config()
    mysqldump = find_mysqldump()

    print(f"[源]   本地库 {local['user']}@{local['host']}:{local['port']}/{local['db']}")
    print(f"[目标] Docker 容器 {container} (root)")
    print(f"[mysqldump] {mysqldump}")

    sql = dump_local(local, mysqldump, exclude_mbti=not args.include_mbti)
    print(f"[dump] 导出 {len(sql)} 字节（mbti_types={'包含' if args.include_mbti else '跳过'}）")

    sql = strip_db_statements(sql)
    import_to_container(container, password, sql, dry_run=args.dry_run)

    if args.dry_run:
        print("[dry-run] 完成（未实际导入）")
    else:
        print("[导入] 完成")
        verify_counts(container, password)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)
