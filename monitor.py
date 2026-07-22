#!/usr/bin/env python3
"""
Apple 官翻商店 Mac mini 库存监控 — GitHub Actions 云端版
运行在 GitHub 服务器上，无需本地电脑开机。
发现 Mac mini 有货时自动推送微信通知（通过 PushPlus）。
"""

import os
import re
import json
import gzip
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta

# ── 配置 ──────────────────────────────────────────────────
TARGET_URL = "https://www.apple.com.cn/shop/refurbished/mac"
KEYWORD = "mac mini"          # 不区分大小写
BASE_URL = "https://www.apple.com.cn"
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")
CST = timezone(timedelta(hours=8))  # 北京时间
# ──────────────────────────────────────────────────────────


def fetch_page(url: str) -> str:
    """抓取页面 HTML（处理 gzip 压缩）"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    raw = resp.read()
    if raw[:2] == b"\x1f\x8b":          # gzip magic bytes
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def extract_products(html: str) -> list:
    """
    从 HTML 中提取所有翻新产品。
    Apple 官翻页面的产品名在 <h3><a>...</a></h3> 标签里。
    同时提取价格和产品链接。
    """
    products = []
    # 匹配 h3 > a 结构（产品名 + 链接）
    h3_pattern = r'<h3[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*</h3>'
    matches = re.findall(h3_pattern, html, re.DOTALL)

    for href, name_html in matches:
        name = re.sub(r"<[^>]+>", "", name_html).strip()
        if not name:
            continue
        link = BASE_URL + href if href.startswith("/") else href

        # 在名称附近搜索价格
        idx = html.find(name_html)
        price = "价格未知"
        if idx >= 0:
            context = html[idx : idx + 3000]
            price_match = re.search(r"[¥￥]\s*[\d,]+", context)
            if price_match:
                price = price_match.group(0)

        products.append({"name": name, "price": price, "link": link})

    return products


def find_mac_mini(products: list) -> list:
    """筛选出 Mac mini 产品"""
    return [p for p in products if KEYWORD in p["name"].lower()]


def send_pushplus(title: str, content: str) -> bool:
    """通过 PushPlus 推送微信通知"""
    if not PUSHPLUS_TOKEN:
        print("⚠️ 未设置 PUSHPLUS_TOKEN 环境变量，跳过微信推送")
        return False

    payload = json.dumps(
        {"token": PUSHPLUS_TOKEN, "title": title, "content": content, "template": "markdown"}
    ).encode("utf-8")

    req = urllib.request.Request(
        "http://www.pushplus.plus/send",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode("utf-8"))
        if result.get("code") == 200:
            print(f"✅ 微信推送成功: {title}")
            return True
        else:
            print(f"❌ 微信推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 微信推送异常: {e}")
        return False


def main():
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"🕐 检查时间: {now} (北京时间)")
    print(f"📡 目标页面: {TARGET_URL}")
    print("-" * 50)

    try:
        html = fetch_page(TARGET_URL)
        print(f"📄 页面大小: {len(html)} 字符")

        products = extract_products(html)
        print(f"📦 发现 {len(products)} 个翻新产品")

        mac_mini_list = find_mac_mini(products)

        if mac_mini_list:
            # ── 有货！推送微信 ──
            print(f"\n🎉🎉🎉 发现 {len(mac_mini_list)} 个 Mac mini 翻新产品！")
            for p in mac_mini_list:
                print(f"  → {p['name']} | {p['price']} | {p['link']}")

            # 构建 Markdown 推送内容
            lines = [
                "## 🎉 Mac mini 官翻有货了！",
                "",
                f"🕐 发现时间: {now}",
                "",
            ]
            for p in mac_mini_list:
                lines.append(f"### {p['name']}")
                lines.append(f"- 💰 价格: **{p['price']}**")
                lines.append(f"- 🔗 购买链接: {p['link']}")
                lines.append("")
            lines.append("> ⚡ 官翻库存变化极快，建议立即下单！")
            lines.append(f"> 🛒 [前往 Apple 官翻商店]({TARGET_URL})")

            content = "\n".join(lines)
            send_pushplus("🎉 Mac mini 官翻有货了！", content)

            print("\n✅ 检查完成: Mac mini 有货，微信通知已发送")

            # GitHub Actions 输出
            gh_output = os.environ.get("GITHUB_OUTPUT")
            if gh_output:
                with open(gh_output, "a") as f:
                    f.write("mac_mini_found=true\n")
        else:
            # ── 没货，安静退出 ──
            print("\nℹ️ Mac mini 暂无货")

            # 显示当前在售类别
            categories = set()
            for p in products:
                n = p["name"].lower()
                if "macbook air" in n:
                    categories.add("MacBook Air")
                elif "macbook pro" in n:
                    categories.add("MacBook Pro")
                elif "imac" in n:
                    categories.add("iMac")
                elif "studio display" in n or "显示器" in n:
                    categories.add("Studio Display")
                elif "mac mini" in n:
                    categories.add("Mac mini")
                elif "mac studio" in n:
                    categories.add("Mac Studio")
                else:
                    categories.add(p["name"][:20])
            if categories:
                print(f"📋 当前在售: {', '.join(sorted(categories))}")
            print("✅ 检查完成: Mac mini 暂无货")

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a") as f:
                f.write(f"error={str(e)}\n")
        raise


if __name__ == "__main__":
    main()
