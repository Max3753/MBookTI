# 云服务器间数据迁移脚本（MBookTI）
#
# 适用场景：试用期 ECS 到期 → 更换整年套餐服务器时，把 MySQL 数据完整搬过去。
#
# 用法：
#   [旧服务器] 导出备份：
#     python migrate_server.py export --container mbookti-mysql-1 --password 142857 [--out /root/mbookti_backup.sql]
#
#   [新服务器] 部署好 docker compose 并启动后，导入备份：
#     python migrate_server.py import --container mbookti-mysql-1 --password 新密码 [--in /root/mbookti_backup.sql]
#
# 参数说明：
#   --container      MySQL 容器名（默认自动探测 mbookti-mysql 前缀）
#   --password       容器 MySQL root 密码（必填；或设环境变量 MYSQL_ROOT_PASSWORD）
#   --out / --in     备份文件路径（默认 /root/mbookti_backup.sql）
#   --dry-run        只打印将执行的命令，不真正执行
#
# 说明：
#   1. export 在「旧服务器」上跑：容器内 mysqldump 导出 → 拷贝到服务器文件系统。
#      之后用 Xftp/SFTP 把备份文件下载到本地，再上传到新服务器。
#   2. import 在「新服务器」上跑：拷贝进容器 → mysql 导入 → 自动验证数据量。
#   3. dump 文件自带 DROP TABLE IF EXISTS + FOREIGN_KEY_CHECKS=0：
#      mbti_types 等所有表会被重建为旧服务器数据，即使新容器已自动 seed 也无冲突。
#   4. 全程 --default-character-set=utf8mb4 二进制流，不受系统 locale 影响。
import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_OUT = "/root/mbookti_backup.sql"
MYSQL_CONTAINER_PREFIX = "mbookti-mysql"


def run(cmd: list, dry_run: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """执行命令；dry_run 时只打印。"""
    print("  $", " ".join(cmd))
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0)
    r = subprocess.run(cmd, capture_output=True)
    if check and r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"命令失败 (exit={r.returncode}): {err}")
    return r


def find_container(dry_run: bool = False) -> str:
    """自动探测 mbookti MySQL 容器名"""
    r = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("无法执行 docker，请确认已安装 Docker 且守护进程在运行")
    names = r.stdout.splitlines()
    for n in names:
        if MYSQL_CONTAINER_PREFIX in n:
            return n
    raise RuntimeError(f"未找到 MySQL 容器（前缀 {MYSQL_CONTAINER_PREFIX}）。当前容器: {names}")


def get_password(args) -> str:
    pwd = args.password or os.environ.get("MYSQL_ROOT_PASSWORD")
    if not pwd:
        raise SystemExit(
            "缺少 MySQL root 密码：请用 --password 参数或设置环境变量 MYSQL_ROOT_PASSWORD"
        )
    return pwd


def cmd_export(args):
    """旧服务器：容器内导出 → 拷贝到服务器文件系统"""
    container = args.container or find_container(args.dry_run)
    pwd = get_password(args)
    out = args.out or DEFAULT_OUT

    print(f"[1/3] 容器内 mysqldump 导出（容器: {container}）")
    inner = (
        f"mysqldump -uroot -p{pwd} --default-character-set=utf8mb4 "
        f"--single-transaction mbookti > /tmp/mbookti_export.sql"
    )
    run(["docker", "exec", container, "sh", "-c", inner], args.dry_run)

    print(f"[2/3] 拷贝到服务器文件系统 {out}")
    run(["docker", "exec", container, "sh", "-c", f"cp /tmp/mbookti_export.sql {out}"], args.dry_run)
    run(["docker", "exec", container, "rm", "-f", "/tmp/mbookti_export.sql"], args.dry_run)

    print("[3/3] 确认备份文件")
    if not args.dry_run:
        r = run(["docker", "exec", container, "sh", "-c", "ls -lh " + out], check=False)
        print(r.stdout.decode("utf-8", errors="replace").strip())

    print()
    print("=" * 56)
    print("导出完成！接下来：")
    print("  1. 用 Xftp/SFTP 把服务器上的 %s 下载到本地" % out)
    print("  2. 再上传到新服务器的同一路径")
    print("  3. 在新服务器上运行: python migrate_server.py import --password 新密码")
    print("=" * 56)


def cmd_import(args):
    """新服务器：拷贝进容器 → 导入 → 验证"""
    container = args.container or find_container(args.dry_run)
    pwd = get_password(args)
    in_path = args.in_path or DEFAULT_OUT

    if not args.dry_run and not Path(in_path).exists():
        raise SystemExit(f"备份文件不存在: {in_path}")

    print(f"[1/3] 拷贝备份进容器（容器: {container}）")
    run(["docker", "cp", in_path, f"{container}:/tmp/mbookti_import.sql"], args.dry_run)

    print("[2/3] 导入 MySQL（dump 自带 DROP TABLE，会覆盖为新服务器数据）")
    inner = (
        f"mysql -uroot -p{pwd} --default-character-set=utf8mb4 mbookti "
        f"< /tmp/mbookti_import.sql"
    )
    r = run(["docker", "exec", container, "sh", "-c", inner], args.dry_run, check=False)
    if not args.dry_run and r.returncode != 0:
        print("[警告] 导入命令退出码非零，以下 stderr 可能含错误：")
        print(r.stderr.decode("utf-8", errors="replace")[:1500])

    run(["docker", "exec", container, "rm", "-f", "/tmp/mbookti_import.sql"], args.dry_run)

    print("[3/3] 验证数据量")
    if not args.dry_run:
        sql = (
            "SELECT 'users',COUNT(*) FROM users UNION ALL "
            "SELECT 'books',COUNT(*) FROM books UNION ALL "
            "SELECT 'mbti_types',COUNT(*) FROM mbti_types UNION ALL "
            "SELECT 'comments',COUNT(*) FROM comments"
        )
        r = run(
            ["docker", "exec", container, "mysql", "-uroot", f"-p{pwd}", "-D", "mbookti", "-N", "-e", sql],
            check=False,
        )
        if r.returncode == 0:
            print(r.stdout.decode("utf-8", errors="replace"))
        else:
            print("[警告] 验证查询失败，请手动检查容器数据")

    print()
    print("=" * 56)
    print("导入完成！")
    print("  前端:  http://<服务器IP>:8080")
    print("  后端:  http://<服务器IP>:8000")
    print("=" * 56)


def main():
    parser = argparse.ArgumentParser(description="MBookTI 云服务器数据迁移")
    sub = parser.add_subparsers(dest="mode", required=True, help="export=旧机导出 / import=新机导入")

    p_export = sub.add_parser("export", help="旧服务器导出备份")
    p_export.add_argument("--container", default=None)
    p_export.add_argument("--password", default=None)
    p_export.add_argument("--out", default=None, help=f"备份输出路径（默认 {DEFAULT_OUT}）")
    p_export.add_argument("--dry-run", action="store_true")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="新服务器导入备份")
    p_import.add_argument("--container", default=None)
    p_import.add_argument("--password", default=None)
    p_import.add_argument("--in", dest="in_path", default=None, help=f"备份文件路径（默认 {DEFAULT_OUT}）")
    p_import.add_argument("--dry-run", action="store_true")
    p_import.set_defaults(func=cmd_import)

    args = parser.parse_args()
    try:
        args.func(args)
    except (RuntimeError, SystemExit) as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
