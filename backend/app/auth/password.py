import bcrypt


def hash_password(password: str) -> str:
    """使用 bcrypt 直接哈希（绕过 passlib —— passlib 1.7.4 与 bcrypt>=4.1 不兼容，
    passlib 会尝试读取已移除的私有属性导致 AttributeError）"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码。兼容 passlib 生成的 $2b$ 前缀 hash（bcrypt 库原生支持）。"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
