# 登录/注册速率限制（进程内存滑动窗口）
# 用途：防暴力破解 / 批量注册。按 IP 与用户名双维度计数。
# 注意：仅限单进程部署（当前形态）。多 worker / 多实例需替换为 Redis 等共享存储。
import time
from collections import defaultdict, deque
from typing import Dict, Deque

from fastapi import HTTPException

WINDOW_SECONDS = 5 * 60  # 滑动窗口：5 分钟
IP_MAX_FAILURES = 20      # 同一 IP 5 分钟内最多失败次数（防扫号）
USER_MAX_FAILURES = 5     # 同一用户名 5 分钟内最多失败次数（防撞库）
IP_MAX_REGISTERS = 10     # 同一 IP 5 分钟内最多注册次数（防批量注册）

FORGOT_WINDOW_SECONDS = 10 * 60  # 忘记密码滑动窗口：10 分钟
IP_MAX_FORGOTS = 5               # 同一 IP 10 分钟内最多 forgot 请求次数（防邮件轰炸）


class _RateLimiter:
    def __init__(self) -> None:
        # key -> 时间戳队列（按时间升序）
        self._ip_failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._user_failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._ip_registers: Dict[str, Deque[float]] = defaultdict(deque)
        self._ip_forgots: Dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, queue: Deque[float], now: float, window: float = WINDOW_SECONDS) -> None:
        while queue and now - queue[0] > window:
            queue.popleft()

    def _check(self, queue: Deque[float], limit: int, now: float, window: float = WINDOW_SECONDS) -> None:
        self._prune(queue, now, window)
        if len(queue) >= limit:
            raise HTTPException(
                status_code=429,
                detail="操作过于频繁，请稍后再试",
            )

    def check_login(self, ip: str, username: str) -> None:
        now = time.time()
        self._check(self._ip_failures[ip], IP_MAX_FAILURES, now)
        self._check(self._user_failures[username], USER_MAX_FAILURES, now)

    def record_login_failure(self, ip: str, username: str) -> None:
        now = time.time()
        self._prune(self._ip_failures[ip], now)
        self._prune(self._user_failures[username], now)
        self._ip_failures[ip].append(now)
        self._user_failures[username].append(now)

    def clear_login(self, ip: str, username: str) -> None:
        """登录成功后清除该维度记录。"""
        self._ip_failures.pop(ip, None)
        self._user_failures.pop(username, None)

    def check_register(self, ip: str) -> None:
        now = time.time()
        self._check(self._ip_registers[ip], IP_MAX_REGISTERS, now)

    def record_register(self, ip: str) -> None:
        now = time.time()
        self._prune(self._ip_registers[ip], now)
        self._ip_registers[ip].append(now)

    def check_forgot(self, ip: str) -> None:
        """忘记密码限流：同一 IP 10 分钟内最多 5 次，超出抛 429。"""
        now = time.time()
        self._check(self._ip_forgots[ip], IP_MAX_FORGOTS, now, FORGOT_WINDOW_SECONDS)

    def record_forgot(self, ip: str) -> None:
        now = time.time()
        self._prune(self._ip_forgots[ip], now, FORGOT_WINDOW_SECONDS)
        self._ip_forgots[ip].append(now)


login_limiter = _RateLimiter()
